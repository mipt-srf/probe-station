import logging

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.pymeasure_base import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.rsu import RSU, RSUOutputMode, setup_rsu_output
from probe_station.measurements.session import Session
from probe_station.measurements.smu._widgets import IvPlotWidget
from probe_station.measurements.smu.fet_ids_vg_runner import run

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SmuFetIdsVgProcedure(BaseProcedure):
    voltage_gate_first = FloatParameter("Gate voltage (first)", units="V", default=-20.0)
    voltage_gate_second = FloatParameter("Gate voltage (second)", units="V", default=20.0)
    voltage_ds = FloatParameter("Drain-source voltage", units="V", default=1.0)
    source = IntegerParameter("Source channel", default=3)
    drain = IntegerParameter("Drain channel", default=1)
    average = IntegerParameter("Intergration coefficient", default=127, minimum=1, maximum=127)
    advanced_config = BooleanParameter("Advanced config", default=False)
    steps = IntegerParameter("Steps", default=100, group_by="advanced_config")
    mode = IntegerParameter("Mode", default=1, group_by="advanced_config")
    gate = IntegerParameter("Gate channel", default=4)
    base = IntegerParameter("Base channel", default=2)

    DATA_COLUMNS = ["Gate Voltage", "Drain-Source Current", "Gate Current", "Time"]

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
            self.voltage_gate_first,
            self.voltage_gate_second,
            self.steps,
            average=self.average,
            drain=self.drain,
            source=self.source,
            mode=self.mode,
            gate=self.gate,
            drain_voltage=self.voltage_ds,
            base=self.base,
        )

        if self.mode == 2:
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
                    "Drain-Source Current": current,
                    "Gate Current": gate_current,
                },
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
            IvPlotWidget("Results Graph", SmuFetIdsVgProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=SmuFetIdsVgProcedure,
            widget_list=widget_list,
            logger=log,
        )
        self.setWindowTitle("Ids (Vg)")


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
