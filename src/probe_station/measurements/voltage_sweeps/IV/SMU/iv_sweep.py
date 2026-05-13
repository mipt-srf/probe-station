import logging

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.common import (
    RSU,
    BaseProcedure,
    BaseWindow,
    RSUOutputMode,
    run_app,
    setup_rsu_output,
)
from probe_station.measurements.session import Session
from probe_station.measurements.voltage_sweeps.IV.SMU.iv_sweep_runner import run
from probe_station.measurements.voltage_sweeps.IV._widgets import IvPlotWidget

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SmuIvSweepProcedure(BaseProcedure):
    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    top_channel = IntegerParameter("Top channel", default=4)
    bottom_channel = IntegerParameter("Bottom channel", default=3)
    average = IntegerParameter("Intergration coefficient", default=127, minimum=1, maximum=127)
    advanced_config = BooleanParameter("Advanced config", default=False)
    steps = IntegerParameter("Steps", default=100, group_by="advanced_config")
    mode = IntegerParameter("Mode", default=1, group_by="advanced_config")
    # compliance = FloatParameter("Current compliance", units="A", default=0.1, group_by="advanced_config")

    DATA_COLUMNS = ["Voltage", "Top electrode current", "Time"]

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire(timeout=60000, reset=False)
        self.b1500.clear_buffer()
        setup_rsu_output(self.b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
        setup_rsu_output(self.b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    def execute(self):
        log.info(f"Starting the {self.__class__}")

        run(
            self.b1500,
            self.first_voltage,
            self.second_voltage,
            self.steps,
            top=self.top_channel,
            # current_comp=self.compliance,
            average=self.average,
            mode=self.mode,
        )

        # mode 1: one LINEAR_DOUBLE sweep → 2*steps output points
        # mode 2: two LINEAR_DOUBLE half-sweeps, each configured with steps//2 and LINEAR_DOUBLE
        if self.mode == 2:
            total_steps = 2 * self.steps - 1
        else:
            total_steps = 2 * self.steps

        for emitted, (time, current, voltage) in enumerate(self.b1500.iter_output(total_steps, 3), start=1):
            self.emit("progress", emitted / total_steps * 100)
            self.emit(
                "results",
                {"Time": time, "Voltage": voltage, "Top electrode current": current},
            )
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                self.b1500.abort()
                self.b1500.force_gnd()
                return

        self.b1500.force_gnd()


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            IvPlotWidget("Results Graph", SmuIvSweepProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=SmuIvSweepProcedure,
            widget_list=widget_list,
            logger=log,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
