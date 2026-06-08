import logging

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.b1500_helpers import channel_letter
from probe_station.measurements.pymeasure_base import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.rsu import RSU, RSUOutputMode, setup_rsu_output
from probe_station.measurements.session import Session
from probe_station.measurements.smu._widgets import IvPlotWidget
from probe_station.measurements.smu.fet_ids_vds_runner import run

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SmuFetIdsVdsProcedure(BaseProcedure):
    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    source_channel = IntegerParameter("Source channel", default=4)
    drain_channel = IntegerParameter("Drain channel", default=3)
    average = IntegerParameter("Intergration coefficient", default=127, minimum=1, maximum=127)
    advanced_config = BooleanParameter("Advanced config", default=False)
    steps = IntegerParameter("Steps", default=100, group_by="advanced_config")
    mode = IntegerParameter("Mode", default=1, group_by="advanced_config")
    gate_channel = IntegerParameter("Gate channel", default=1)
    gate_voltage = FloatParameter("Gate voltage", units="V", default=0)
    # compliance = FloatParameter("Current compliance", units="A", default=0.1, group_by="advanced_config")

    DATA_COLUMNS = ["Voltage", "Source electrode current", "Gate current", "Time"]

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
            top=self.source_channel,
            # current_comp=self.compliance,
            average=self.average,
            mode=self.mode,
            gate=self.gate_channel,
            gate_voltage=self.gate_voltage,
        )

        if self.mode == 2:
            total_steps = 2 * self.steps - 1
        else:
            total_steps = 2 * self.steps

        source_letter = channel_letter(self.source_channel)
        gate_letter = channel_letter(self.gate_channel)

        # Each step returns 5 tokens: time + current for the swept (drain) and gate
        # channels, plus the swept source voltage. Route them by channel/type prefix so
        # the columns stay correct regardless of the instrument's token order.
        for emitted, tokens in enumerate(self.b1500.iter_output(total_steps, 5, raw=True), start=1):
            time = voltage = current = gate_current = None
            for token in tokens:
                channel = token[1]
                data_type = token[2]
                value = float(token[3:])
                if data_type == "T" and channel == source_letter:
                    time = value
                elif data_type == "I" and channel == source_letter:
                    current = value
                elif data_type == "I" and channel == gate_letter:
                    gate_current = value
                elif data_type == "V":
                    voltage = value

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
                log.warning("Caught the stop flag in the procedure")
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
            logger=log,
        )
        self.setWindowTitle("Ids (Vds)")


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
