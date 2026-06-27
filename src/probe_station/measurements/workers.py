"""Custom Pymeasure :class:`Worker` that captures procedure ``end_time``.

Pymeasure freezes the CSV metadata header before ``procedure.execute()``
runs (``Worker.run``: ``startup`` → ``evaluate_metadata`` →
``store_metadata`` → ``execute``), so any value captured during or after
``execute`` cannot reach the header through the standard flow.
:class:`EndTimeWorker` works around this in two small steps:

1. After ``super().run()`` returns — at which point ``Worker.shutdown``
   has called ``recorder.stop()``, which enqueues a sentinel and joins
   the recorder thread (``QueueListener.stop``), so the data file is no
   longer being written — patch the existing metadata header by
   replacing the literal ``End time: 0`` line with the real value set
   in :meth:`BaseProcedure.shutdown`. This avoids appending a second
   metadata block (which is what calling :meth:`Results.store_metadata`
   again would do).

   The patched file is written to a sibling temp file and then
   atomically moved into place with :func:`os.replace`, *not* rewritten
   in place. The live GUI plot keeps re-reading the result file after the
   run finishes (``Manager._finish`` → ``ResultsCurve.update_data`` →
   ``Results.data``), and an in-place ``write_text`` truncates the file
   before rewriting it, so a read landing in that window sees a partial
   file and the incremental reader folds a corrupt trailing row into the
   curve's cached data — the "phantom point" that never appears when the
   completed file is reopened. This is most visible for WGFMU procedures,
   which emit the whole sweep at once (``emit("batch results", ...)``):
   the result file is freshly written in one burst right as the header
   patch runs, whereas row-by-row procedures finish writing long before.
   An atomic replace lets every concurrent read see either the old or the
   new file in full, never a truncated one.

2. Replace ``pymeasure.display.manager.Worker`` with this subclass at
   import time so GUI runs dispatched via
   :class:`~pymeasure.display.manager.Manager` pick up the same
   behaviour. Pymeasure's ``Manager.next()`` hard-codes the ``Worker``
   reference, so a small patch is the least-invasive way to swap it.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import pymeasure.display.manager as _pymeasure_manager
from pymeasure.experiment.results import Results
from pymeasure.experiment.workers import Worker

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


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
            logger.exception("Failed to patch end_time into CSV header")

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
                logger.warning("End time placeholder not found in %s; header left untouched", filename)
                continue
            self._atomic_write(path, text.replace(needle, replacement, 1))

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        """Replace *path*'s contents with *text* atomically.

        Writes a sibling ``.tmp`` file and :func:`os.replace`\\ s it over
        *path*, so a concurrent reader (the live GUI plot) only ever sees the
        old or new file in full, never a half-rewritten one. On Windows the
        replace fails while another handle has the destination open, so retry a
        few times before giving up and leaving the original file intact.
        """
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(text, encoding=Results.ENCODING)
        for _ in range(10):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                time.sleep(0.02)
        logger.warning("Could not replace %s with patched header (file kept open elsewhere)", path)
        tmp.unlink(missing_ok=True)


_pymeasure_manager.Worker = EndTimeWorker
