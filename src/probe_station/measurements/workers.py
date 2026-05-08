"""Custom Pymeasure :class:`Worker` that captures procedure ``end_time``.

Pymeasure freezes the CSV metadata header before ``procedure.execute()``
runs (``Worker.run``: ``startup`` → ``evaluate_metadata`` →
``store_metadata`` → ``execute``), so any value captured during or after
``execute`` cannot reach the header through the standard flow.
:class:`EndTimeWorker` works around this in two small steps:

1. After ``super().run()`` returns — at which point ``Worker.shutdown``
   has called ``recorder.stop()``, which enqueues a sentinel and joins
   the recorder thread (``QueueListener.stop``), so the data file is no
   longer being written — patch the existing metadata header in place
   by replacing the literal ``End time: 0`` line with the real value
   set in :meth:`BaseProcedure.shutdown`. This avoids appending a
   second metadata block (which is what calling
   :meth:`Results.store_metadata` again would do).

2. Replace ``pymeasure.display.manager.Worker`` with this subclass at
   import time so GUI runs dispatched via
   :class:`~pymeasure.display.manager.Manager` pick up the same
   behaviour. Pymeasure's ``Manager.next()`` hard-codes the ``Worker``
   reference, so a small patch is the least-invasive way to swap it.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pymeasure.display.manager as _pymeasure_manager
from pymeasure.experiment.results import Results
from pymeasure.experiment.workers import Worker

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class EndTimeWorker(Worker):
    """:class:`Worker` that patches ``end_time`` into the CSV header in place.

    Lets ``end_time`` (set in :meth:`BaseProcedure.shutdown`) land in
    the CSV header alongside ``start_time``, without leaving behind a
    duplicate metadata block.
    """

    def run(self) -> None:
        super().run()
        try:
            self._patch_end_time_in_header()
        except Exception:
            log.exception("Failed to patch end_time into CSV header")

    def _patch_end_time_in_header(self) -> None:
        end_time = getattr(self.procedure, "end_time", 0)
        if end_time == 0:
            return
        needle = f"{Results.COMMENT}\tEnd time: 0{Results.LINE_BREAK}"
        value = str(end_time).encode("unicode_escape").decode("utf-8")
        replacement = f"{Results.COMMENT}\tEnd time: {value}{Results.LINE_BREAK}"
        for filename in self.results.data_filenames:
            path = Path(filename)
            text = path.read_text(encoding=Results.ENCODING)
            if needle not in text:
                log.warning("End time placeholder not found in %s; header left untouched", filename)
                continue
            path.write_text(text.replace(needle, replacement, 1), encoding=Results.ENCODING)


_pymeasure_manager.Worker = EndTimeWorker
