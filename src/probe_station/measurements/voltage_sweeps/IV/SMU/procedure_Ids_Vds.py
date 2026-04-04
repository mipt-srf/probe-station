import logging
import sys

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter
from qtpy.QtCore import QLocale

from probe_station.measurements.common import BaseProcedure, BaseWindow, connect_instrument
from probe_station.measurements.voltage_sweeps.IV.SMU.script_Ids_Vds import get_data, run
from probe_station.measurements.voltage_sweeps.IV.widgets import IvPlotWidget
from probe_station.logging_setup import setup_file_logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class IvSweepProcedure(BaseProcedure):
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

    DATA_COLUMNS = ["Voltage", "Source electrode current", "Time"]

    def startup(self):
        super().startup()
        self.b1500 = connect_instrument(timeout=60000, reset=False)

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
        times, voltages, currents = get_data(self.b1500)
        # print(f"len(times) = {len(times), len(voltages), len(currents)}")
        # print(voltages[:20])

        self.emit(
            "batch results",
            {"Time": times, "Voltage": voltages, "Source electrode current": currents},
        )

        times, voltages, currents = get_data(self.b1500)
        # print(f"len(times) = {len(times), len(voltages), len(currents)}")
        # print(currents[:20])

        self.emit(
            "batch results",
            {"Time": times, "Voltage": voltages, "Source electrode current": currents},
        )


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            IvPlotWidget("Results Graph", IvSweepProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=IvSweepProcedure,
            widget_list=widget_list,
            logger=log,
        )
        self.setWindowTitle("Ids (Vds)")


if __name__ == "__main__":
    setup_file_logging("logs")
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
