import logging

from pymeasure.display.widgets import LogWidget

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.pymeasure_base import BaseWindow, run_app
from probe_station.measurements.smu.quasistatic_cv import QscvProcedureBase
from probe_station.measurements.smu.quasistatic_cv_runner import measure_offset

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class QscvOffsetCancelProcedure(QscvProcedureBase):
    """Measure the open-terminal capacitance offset for QSCV and enable cancel.

    Run this with the probe tips **lifted** (device terminals open). It applies
    the same QSCV conditions as the sweep -- match the current range in
    particular -- measures the residual fixture/cable/probe capacitance,
    enables the offset cancel, and logs the value. Subsequent QSCV sweeps run
    with "Apply offset cancel" then subtract it. Re-run after changing the
    current range, as the offset is only valid for the range it was taken at.
    """

    # No sweep curve: the result is a single offset value reported to the log.
    DATA_COLUMNS = []

    def execute(self):
        log.info("Measuring open-terminal QSCV offset -- ensure the probe tips are lifted (terminals open).")
        try:
            offset = measure_offset(self.b1500, **self._setup_kwargs())
            log.info(
                "Offset = %.4e F (%.3f pF). Offset cancel is now enabled for QSCV sweeps at this range.",
                offset,
                offset * 1e12,
            )
        finally:
            # Return all electrodes to 0 V and clear any pending error so it
            # cannot surface in the next measurement.
            self.b1500.force_gnd()
            self._consume_pending_errors()


class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__(
            procedure_class=QscvOffsetCancelProcedure,
            widget_list=(LogWidget("Experiment Log"),),
            logger=log,
        )
        self.setWindowTitle("QSCV Offset Cancel")


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
