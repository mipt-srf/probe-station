import logging

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter, ListParameter

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.pymeasure_base import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.rsu import RSU, RSUOutputMode, setup_rsu_output
from probe_station.measurements.session import Session
from probe_station.measurements.smu._sweep_mode import SmuSweepMode
from probe_station.measurements.smu._widgets import IvPlotWidget
from probe_station.measurements.smu.fet_ids_vg_runner import run

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SmuFetIdsVgProcedure(BaseProcedure):
    gate_voltage_first = FloatParameter("Gate voltage (first)", units="V", default=-20.0)
    gate_voltage_second = FloatParameter("Gate voltage (second)", units="V", default=20.0)
    drain_voltage = FloatParameter("Drain voltage", units="V", default=1.0)
    source_channel = IntegerParameter("Source channel", default=3)
    drain_channel = IntegerParameter("Drain channel", default=1)
    averaging = IntegerParameter("Integration coefficient", default=127, minimum=1, maximum=127)
    advanced_config = BooleanParameter("Advanced config", default=False)
    steps = IntegerParameter("Steps", default=100, group_by="advanced_config")
    mode = ListParameter(
        "Mode",
        default=SmuSweepMode.START_TO_STOP.name,
        choices=[member.name for member in SmuSweepMode],
        group_by="advanced_config",
    )
    gate_channel = IntegerParameter("Gate channel", default=4)
    base_channel = IntegerParameter("Base channel", default=2)

    DATA_COLUMNS = ["Gate Voltage", "Drain Current", "Gate Current", "Time"]

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
            self.gate_voltage_first,
            self.gate_voltage_second,
            self.steps,
            average=self.averaging,
            drain=self.drain_channel,
            source=self.source_channel,
            mode=SmuSweepMode[self.mode].value,
            gate=self.gate_channel,
            drain_voltage=self.drain_voltage,
            base=self.base_channel,
        )

        if SmuSweepMode[self.mode] is SmuSweepMode.FROM_ZERO:
            total_steps = 2 * self.steps - 1
        else:
            total_steps = 2 * self.steps

        # Each step returns 5 values: time + current for the drain and gate
        # channels, then the swept gate voltage.
        for emitted, (time, current, _gate_time, gate_current, voltage) in enumerate(
            self.b1500.iter_output(total_steps, 5), start=1
        ):
            self.emit("progress", emitted / total_steps * 100)
            self.emit(
                "results",
                {
                    "Time": time,
                    "Gate Voltage": voltage,
                    "Drain Current": current,
                    "Gate Current": gate_current,
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
            IvPlotWidget("Results Graph", SmuFetIdsVgProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=SmuFetIdsVgProcedure,
            widget_list=widget_list,
            logger=logger,
        )
        self.setWindowTitle("Ids (Vg)")


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
