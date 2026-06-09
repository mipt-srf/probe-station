import threading
from functools import wraps

from keysight_b1530a import (
    WGFMU,
    add_vector,
    add_vectors,
    clear,
    close_session,
    create_pattern,
    execute,
    get_channel_ids,
    initialize,
    open_session,
    set_measure_event,
    wait_until_completed,
)
from keysight_b1530a.enums import (  # noqa: F401
    WGFMUMeasureCurrentRange,
    WGFMUMeasureEvent,
    WGFMUMeasureMode,
    WGFMUOperationMode,
)
from pymeasure.instruments.agilent.agilentB1500 import AgilentB1500


def _synchronized(method):
    """Serialize a VISA I/O method on the instrument's re-entrant ``_io_lock``.

    The B1500 owns a single shared connection (one instance per process; see
    :class:`~probe_station.measurements.session.Session`). Concurrent worker
    threads must never interleave traffic on it, or one thread's reply splices
    into another's -- e.g. a liveness-probe ``*IDN?`` response landing in the
    middle of a running sweep's data stream. Holding the lock per call makes
    each transaction atomic; the lock is re-entrant so compound calls
    (``ask`` = write + read) nest, and so :meth:`B1500.iter_output` can hold it
    across an entire sweep while still issuing reads underneath.
    """

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._io_lock:
            return method(self, *args, **kwargs)

    return wrapper


class B1500(AgilentB1500):
    """Subclass of the AgilentB1500 to add WGFMU support and some custom methods."""

    def __init__(self, adapter="USB1::0x0957::0x0001::0001::0::INSTR", **kwargs):
        # Created before super().__init__(), which already drives I/O through
        # the synchronized methods below.
        self._io_lock = threading.RLock()
        super().__init__(adapter, **kwargs)
        self._wgfmu_session_opened = False
        self.initialize_all_smus()
        self.initialize_all_spgus()
        self.initialize_cmu()
        self._init_wgfmu_channels()

    # --- Serialized VISA I/O ------------------------------------------------
    # Every entry point that touches the shared connection takes _io_lock so
    # concurrent threads never interleave traffic. These four cover all paths:
    # ``ask`` for queries and property reads, ``write`` for commands and
    # property writes, ``read``/``read_bytes`` for the parent's data reads
    # (read_data/read_channels) and our iter_output stream.

    @_synchronized
    def write(self, command, **kwargs):
        return super().write(command, **kwargs)

    @_synchronized
    def read(self, **kwargs):
        return super().read(**kwargs)

    @_synchronized
    def read_bytes(self, count, **kwargs):
        return super().read_bytes(count, **kwargs)

    @_synchronized
    def ask(self, command, query_delay=None):
        return super().ask(command, query_delay)

    def _init_wgfmu_channels(self):
        """Initialize the WGFMU channels."""
        self.open_wgfmu_session()
        channel_ids = self.query_wgfmu_channels()
        self.wgfmus: dict[int, WGFMU] = {}
        for i, channel_id in enumerate(channel_ids, start=1):
            wgfmu = WGFMU(id=channel_id)
            setattr(self, f"wgfmu{i}", wgfmu)
            self.wgfmus[i] = wgfmu

    def open_wgfmu_session(self):
        """Open a session to the WGFMU module."""
        if not self._wgfmu_session_opened:
            open_session(self.adapter.resource_name)
            self._wgfmu_session_opened = True

    def close_wgfmu_session(self):
        """Close the session to the WGFMU module."""
        if self._wgfmu_session_opened:
            close_session()  # Note: will cause the error if the session was closed already from outside
            self._wgfmu_session_opened = False

    @wraps(get_channel_ids)
    def query_wgfmu_channels(self):
        return get_channel_ids()

    @wraps(execute)
    def run_wgfmu_measurement(self):
        execute()
        wait_until_completed()

    @wraps(create_pattern)
    def create_wgfmu_pattern(self, name: str, start_voltage: float):
        return create_pattern(name, start_voltage)

    @wraps(add_vector)
    def add_vector_to_wgfmu_pattern(self, pattern_name: str, voltage: float, duration: float):
        add_vector(pattern_name, voltage, duration)

    @wraps(add_vectors)
    def add_vectors_to_wgfmu_pattern(self, pattern_name: str, voltages: list[float], durations: list[float]):
        add_vectors(pattern_name, voltages, durations)

    @wraps(set_measure_event)
    def set_wgfmu_measure_event(
        self,
        pattern_name: str,
        event_name: str,
        points: int,
        interval: float,
        average: float,
        mode: WGFMUMeasureEvent = WGFMUMeasureEvent.AVERAGED,
        start_time: float = 0.0,
    ):
        set_measure_event(pattern_name, event_name, points, interval, average, mode, start_time)

    @wraps(initialize)
    def initialize_wgfmu(self):
        initialize()

    @wraps(clear)
    def clear_wgfmu(self):
        clear()

    def iter_output(self, total_steps: int, values_per_step: int):
        """Read sweep output step-by-step (B1500 guide section 1-19).

        Yields tuples of `values_per_step` floats, one tuple per sweep step.
        Call after send_trigger() has been issued.

        Uses read_bytes instead of read() to avoid waiting for end-of-message (EOM),
        enabling real-time per-step readout when FMT mode 1 is active.
        Reads until comma/newline delimiters so token byte length does not need to be known.
        """
        resource = self.adapter.connection
        buf = bytearray()

        def next_value() -> float:
            while True:
                for i, byte in enumerate(buf):
                    if byte in (ord(","), ord("\r"), ord("\n")):
                        token = buf[:i].decode("ascii")
                        del buf[: i + 1]
                        if token:
                            return float(token[3:])
                        break  # empty token (e.g. \n after \r), keep scanning
                buf.extend(resource.read_bytes(16, break_on_termchar=True))

        # Hold the I/O lock for the whole sweep so nothing else (e.g. a Session
        # liveness probe issuing *IDN?) can interleave traffic on the shared
        # connection mid-stream. Released when the generator is exhausted,
        # closed (procedure returns early on stop), or raises.
        with self._io_lock:
            for _ in range(total_steps):
                yield tuple(next_value() for _ in range(values_per_step))
