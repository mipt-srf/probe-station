"""Process-wide B1500 instrument session management.

A single :class:`Session` owns the lazily-opened :class:`B1500` connection
for the lifetime of the process. Procedures and orchestrators acquire
the shared handle via :meth:`Session.acquire`; the underlying connection
is opened on first use, reused thereafter, and closed at process exit.

The singleton is forward-compatible with three entry points without any
of them needing to know about it:

* Standalone procedure GUIs (``python -m ...procedure``).
* Scripted sequential orchestrators such as
  :mod:`probe_station.experiments.ultimate`.
* The current subprocess-based launcher (each subprocess holds its own
  session, no regression vs. the per-procedure-reconnect baseline).

The future single-process MDI launcher (SRF-158) becomes additive: the
same :class:`Session` works unchanged once windows share one process.

Note: the underlying ``keysight_b1530a`` library is process-global, so at
most one live :class:`B1500` instance can safely exist per process;
:class:`Session` makes that invariant explicit.
"""

from __future__ import annotations

import atexit
import logging
import threading

from probe_station.measurements.b1500 import B1500
from probe_station.measurements.common import connect_instrument

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Session:
    """Process-wide singleton owning the shared B1500 connection.

    All access goes through classmethods; the class is not instantiable.
    The first :meth:`acquire` call opens a VISA session; subsequent calls
    reuse it. ``atexit`` closes the connection on process exit; an
    explicit :meth:`close` is also available for orchestrators that want
    deterministic shutdown.

    A liveness probe on each :meth:`acquire` reopens the connection if
    the instrument has become unreachable since the last use (cable
    pulled, instrument power-cycled, VISA timeout, etc.).

    Example::

        from probe_station.measurements.session import Session

        b1500 = Session.acquire()
        b1500.clear_wgfmu()
        b1500.initialize_wgfmu()
    """

    _instance: B1500 | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        raise TypeError("Session is not instantiable; use Session.acquire().")

    @classmethod
    def acquire(cls, *, timeout: int = 60_000, reset: bool = False) -> B1500:
        """Return the shared B1500 handle, opening lazily on first use.

        :param timeout: VISA timeout in milliseconds. Only applied when
            a new connection is opened; ignored on reuse.
        :param reset: If ``True``, reset the instrument on first open or
            after dead-handle recovery. Ignored on reuse; call
            :meth:`reconnect` to force a fresh session with reset.
        """
        with cls._lock:
            if cls._instance is not None and not cls._probe_alive(cls._instance):
                log.warning("B1500 handle is dead; reconnecting")
                cls._close_locked()
            if cls._instance is None:
                cls._instance = connect_instrument(timeout=timeout, reset=reset)
            return cls._instance

    @classmethod
    def reconnect(cls, *, timeout: int = 60_000, reset: bool = False) -> B1500:
        """Force a reconnect: close any current handle and open a fresh one."""
        with cls._lock:
            cls._close_locked()
            cls._instance = connect_instrument(timeout=timeout, reset=reset)
            return cls._instance

    @classmethod
    def close(cls) -> None:
        """Close the shared B1500 connection if open. Idempotent."""
        with cls._lock:
            cls._close_locked()

    @classmethod
    def is_open(cls) -> bool:
        """Whether the singleton currently holds a handle.

        Cheap; does not perform a liveness check. See :meth:`is_alive`.
        """
        with cls._lock:
            return cls._instance is not None

    @classmethod
    def is_alive(cls) -> bool:
        """Whether a handle is open and the instrument responds.

        Performs a VISA query, so call sparingly.
        """
        with cls._lock:
            return cls._instance is not None and cls._probe_alive(cls._instance)

    @classmethod
    def _close_locked(cls) -> None:
        if cls._instance is None:
            return
        try:
            cls._instance.adapter.close()
        except Exception:
            log.exception("Error closing B1500 adapter")
        finally:
            cls._instance = None

    @staticmethod
    def _probe_alive(b1500: B1500) -> bool:
        try:
            return bool(b1500.id)
        except Exception:
            return False


atexit.register(Session.close)
