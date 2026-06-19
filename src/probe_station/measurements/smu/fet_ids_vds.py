import logging

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.pymeasure_base import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.rsu import RSU, RSUOutputMode, setup_rsu_output
from probe_station.measurements.session import Session
from probe_station.measurements.smu._widgets import IvPlotWidget
from probe_station.measurements.smu.fet_ids_vds_runner import run

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SmuFetIdsVdsProcedure(BaseProcedure):
    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    source_channel = IntegerParameter("Source channel", default=3)
    drain_channel = IntegerParameter("Drain channel", default=1)
    averaging = IntegerParameter("Integration coefficient", default=127, minimum=1, maximum=127)
    advanced_config = BooleanParameter("Advanced config", default=False)
    steps = IntegerParameter("Steps", default=100, group_by="advanced_config")
    mode = IntegerParameter("Mode", default=1, group_by="advanced_config")
    gate_channel = IntegerParameter("Gate channel", default=4)
    gate_voltage = FloatParameter("Gate voltage", units="V", default=0)
    base_channel = IntegerParameter("Base channel", default=2)
    # compliance = FloatParameter("Current compliance", units="A", default=0.1, group_by="advanced_config")

    DATA_COLUMNS = ["Voltage", "Source electrode current", "Gate current", "Time"]

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire(timeout=60000, reset=False)
        self.b1500.clear_buffer()
        setup_rsu_output(self.b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
        setup_rsu_output(self.b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    def execute(self):
        logger.info(f"Starting the {self.__class__}")

        run(
            self.b1500,
            self.first_voltage,
            self.second_voltage,
            self.steps,
            top=self.source_channel,
            bottom=self.drain_channel,
            # current_comp=self.compliance,
            average=self.averaging,
            mode=self.mode,
            gate=self.gate_channel,
            gate_voltage=self.gate_voltage,
            base=self.base_channel,
        )

        if self.mode == 2:
            total_steps = 2 * self.steps - 1
        else:
            total_steps = 2 * self.steps

        # Each step returns 5 values: time + current for the swept (drain) and gate
        # channels, then the swept source voltage.
        for emitted, (time, current, _gate_time, gate_current, voltage) in enumerate(
            self.b1500.iter_output(total_steps, 5), start=1
        ):
            self.emit("progress", emitted / total_steps * 100)
            self.emit(
                "results",
                {
                    "Time": time,
                    "Voltage": voltage,
                    "Source electrode current": current,
                    "Gate current": gate_current,
                },
            )
            if self.should_stop():
                logger.warning("Caught the stop flag in the procedure")
                self.b1500.abort()
                self.b1500.force_gnd()
                return

        self.b1500.force_gnd()


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            IvPlotWidget("Results Graph", SmuFetIdsVdsProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=SmuFetIdsVdsProcedure,
            widget_list=widget_list,
            logger=logger,
        )
        self.setWindowTitle("Ids (Vds)")


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
