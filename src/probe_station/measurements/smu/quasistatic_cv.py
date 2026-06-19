import logging

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.pymeasure_base import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.rsu import RSU, RSUOutputMode, setup_rsu_output
from probe_station.measurements.session import Session
from probe_station.measurements.smu._widgets import IvPlotWidget
from probe_station.measurements.smu.quasistatic_cv_runner import VALUES_PER_STEP, run

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# After an auto abort the B1500 pads the remaining sweep points with dummy data
# (199.999E+99). Any real capacitance or current is far below this.
DUMMY_DATA_THRESHOLD = 1e99


class QscvProcedureBase(BaseProcedure):
    """Shared measurement-condition parameters and helpers for QSCV procedures.

    Subclassed by the sweep (:class:`SmuQuasistaticCvProcedure`) and the
    open-terminal offset calibration
    (:class:`~probe_station.measurements.smu.quasistatic_cv_offset.QscvOffsetCancelProcedure`)
    so both run under identical conditions. Not launched on its own.
    """

    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    step_voltage = FloatParameter("Sweep step voltage", units="V", default=0.1)
    c_voltage = FloatParameter("Capacitance measurement voltage", units="V", default=0.1)
    hold_time = FloatParameter("Hold time", units="s", default=5)
    # QSR current measurement range code: -9=10pA, -10=100pA, -11=1nA, -12=10nA,
    # -13=100nA, -14=1uA. Must cover ~C*cvoltage/cinteg or the sweep aborts
    # (Error 242); -11 suits tiny gate caps, larger devices need a wider range.
    current_range = IntegerParameter("Current range code", default=-11, minimum=-14, maximum=-9)

    advanced_config = BooleanParameter("Advanced config", default=False)
    integration_time = FloatParameter("Integration time", units="s", default=0.1, group_by="advanced_config")
    delay_time = FloatParameter("Delay time", units="s", default=0.0, group_by="advanced_config")
    auto_abort = BooleanParameter("Auto abort", default=True, group_by="advanced_config")
    current_compliance = FloatParameter("Current compliance", units="A", default=0.1, group_by="advanced_config")
    gate_channel = IntegerParameter("Gate channel", default=4, group_by="advanced_config")
    drain_channel = IntegerParameter("Drain channel", default=1, group_by="advanced_config")
    source_channel = IntegerParameter("Source channel", default=3, group_by="advanced_config")
    base_channel = IntegerParameter("Base channel", default=2, group_by="advanced_config")

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire(timeout=60000, reset=False)
        self.b1500.clear_buffer()
        setup_rsu_output(self.b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
        setup_rsu_output(self.b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    def _setup_kwargs(self):
        """QSCV setup keyword arguments shared by the sweep and the offset cal."""
        return {
            "start": self.first_voltage,
            "stop": self.second_voltage,
            "step_voltage": self.step_voltage,
            "c_voltage": self.c_voltage,
            "hold": self.hold_time,
            "integration_time": self.integration_time,
            "delay": self.delay_time,
            "current_range": self.current_range,
            "current_comp": self.current_compliance,
            "auto_abort": self.auto_abort,
            "gate": self.gate_channel,
            "drain": self.drain_channel,
            "source": self.source_channel,
            "base": self.base_channel,
        }

    def _consume_pending_errors(self):
        """Drain the instrument error queue, logging anything left behind.

        A QSCV auto abort leaves Error 242 ("QSCV measurement was aborted")
        pending. Left in the queue it would crash the *next* procedure on its
        first ``check_errors()`` (e.g. the CMU CV sweep failing at
        ``time_stamp = True``), so consume it here and explain how to fix it.
        Reading ``ERRX?`` pops one error at a time; the loop ends when the
        queue is empty (capped to stay bounded if the queue never clears).
        """
        for _ in range(32):
            try:
                self.b1500.check_errors()
            except Exception as e:  # noqa: BLE001 -- drain whatever the queue holds
                if "242" in str(e):
                    logger.warning(
                        "QSCV measurement was aborted by the instrument (Error 242): the "
                        "capacitance current likely exceeded the measurement range, or the "
                        "SMU oscillated into the load. Widen the current range, increase the "
                        "integration time, or lower the capacitance measurement voltage. "
                        "Recorded data may be incomplete."
                    )
                else:
                    logger.warning("Pending instrument error after QSCV: %s", e)
            else:
                return
        logger.warning("Instrument error queue did not clear after QSCV.")


class SmuQuasistaticCvProcedure(QscvProcedureBase):
    """Quasi-static CV (QSCV) sweep using the B1500 SMU-based ``MM 13`` measurement.

    One SMU sweeps the gate voltage and measures the gate capacitance from the
    charge needed to step the output by the capacitance measurement voltage;
    the leakage current is measured and compensated at every step. Drain,
    source and substrate are held at 0 V. See the B1500 Programming Guide,
    "Quasi-static CV Measurements" (page 3-61).
    """

    offset_cancel = BooleanParameter("Apply offset cancel", default=False)

    DATA_COLUMNS = ["Voltage", "Capacitance", "Leakage current", "Time"]

    def execute(self):
        logger.info(f"Starting the {self.__class__}")
        if self.offset_cancel:
            logger.info(
                "Offset cancel ON: subtracting the last measured open-terminal offset. "
                "Run the QSCV offset calibration first if you have not for this current range."
            )
        try:
            steps = run(self.b1500, offset_cancel=self.offset_cancel, **self._setup_kwargs())

            # Each step returns time, leakage current, capacitance and the swept
            # gate voltage, in that order.
            for emitted, (time, leakage, capacitance, voltage) in enumerate(
                self.b1500.iter_output(steps, VALUES_PER_STEP), start=1
            ):
                self.emit("progress", emitted / steps * 100)
                # After an auto abort the instrument pads the sweep with dummy
                # data (199.999E+99); skip it so it does not pollute the plot.
                if abs(capacitance) < DUMMY_DATA_THRESHOLD:
                    self.emit(
                        "results",
                        {
                            "Time": time,
                            "Voltage": voltage,
                            "Capacitance": capacitance,
                            "Leakage current": leakage,
                        },
                    )
                if self.should_stop():
                    logger.warning("Caught the stop flag in the procedure")
                    self.b1500.abort()
                    return
        finally:
            # Always return every electrode to 0 V (DZ): a failed read mid-sweep
            # must not leave the gate biased, which would rewrite a FeFET's state.
            self.b1500.force_gnd()
            # Consume any pending error (notably a QSCV auto-abort, Error 242)
            # so it cannot surface in the next measurement's check_errors().
            self._consume_pending_errors()


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            IvPlotWidget("Results Graph", SmuQuasistaticCvProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=SmuQuasistaticCvProcedure,
            widget_list=widget_list,
            logger=logger,
        )
        self.setWindowTitle("Quasi-static CV")


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
