"""Custom Pymeasure :class:`Worker` that captures procedure ``end_time``.

Pymeasure freezes the CSV metadata header before ``procedure.execute()``
runs (``Worker.run``: ``startup`` → ``evaluate_metadata`` →
``store_metadata`` → ``execute``), so any value captured during or after
``execute`` cannot reach the header through the standard flow.
:class:`EndTimeWorker` works around this in two small steps:

1. Inject the :class:`~pymeasure.experiment.results.Results` object into
   the procedure (as ``procedure._results``) before the parent
   ``Worker.run`` starts. :class:`~probe_station.measurements.common.BaseProcedure`
   uses that handle from its ``shutdown()`` to call
   ``self.evaluate_metadata()`` + ``results.store_metadata()`` again,
   inserting an updated metadata block (with ``end_time`` filled in)
   immediately after the original.

2. Replace ``pymeasure.display.manager.Worker`` with this subclass at
   import time so GUI runs dispatched via
   :class:`~pymeasure.display.manager.Manager` pick up the same
   behaviour. Pymeasure's ``Manager.next()`` hard-codes the ``Worker``
   reference, so a small patch is the least-invasive way to swap it.
"""

from __future__ import annotations

import pymeasure.display.manager as _pymeasure_manager
from pymeasure.experiment.workers import Worker


class EndTimeWorker(Worker):
    """:class:`Worker` that exposes ``self.results`` to the procedure.

    The injection lets :meth:`BaseProcedure.shutdown` re-store metadata
    after ``execute()`` completes, so ``end_time`` lands in the CSV
    header alongside ``start_time``.
    """

    def run(self) -> None:
        self.results.procedure._results = self.results
        super().run()


_pymeasure_manager.Worker = EndTimeWorker
