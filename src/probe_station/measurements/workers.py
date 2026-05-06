"""Custom Pymeasure :class:`Worker` that captures procedure ``end_time``.

Pymeasure freezes the CSV metadata header before ``procedure.execute()``
runs (``Worker.run``: ``startup`` → ``evaluate_metadata`` →
``store_metadata`` → ``execute``), so any value captured during or after
``execute`` cannot reach the header through the standard flow.
:class:`EndTimeWorker` works around this in two small steps:

1. After ``super().run()`` returns — at which point ``Worker.shutdown``
   has called ``recorder.stop()``, which enqueues a sentinel and joins
   the recorder thread (``QueueListener.stop``), so the data file is no
   longer being written — re-call ``evaluate_metadata`` +
   ``results.store_metadata``. ``BaseProcedure.shutdown`` has set
   ``end_time``, so this second store inserts an updated metadata block
   with the real value.

2. Replace ``pymeasure.display.manager.Worker`` with this subclass at
   import time so GUI runs dispatched via
   :class:`~pymeasure.display.manager.Manager` pick up the same
   behaviour. Pymeasure's ``Manager.next()`` hard-codes the ``Worker``
   reference, so a small patch is the least-invasive way to swap it.
"""

from __future__ import annotations

import logging

import pymeasure.display.manager as _pymeasure_manager
from pymeasure.experiment.workers import Worker

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class EndTimeWorker(Worker):
    """:class:`Worker` that re-stores metadata after the procedure ends.

    Lets ``end_time`` (set in :meth:`BaseProcedure.shutdown`) land in
    the CSV header alongside ``start_time``.
    """

    def run(self) -> None:
        super().run()
        try:
            self.procedure.evaluate_metadata()
            self.results.store_metadata()
        except Exception:
            log.exception("Failed to re-store metadata with end_time")


_pymeasure_manager.Worker = EndTimeWorker
