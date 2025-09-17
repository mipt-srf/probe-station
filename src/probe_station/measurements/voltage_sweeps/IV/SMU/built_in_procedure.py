import logging
import sys

import numpy as np
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter, Procedure

from probe_station.measurements.common import connect_instrument
from probe_station.measurements.voltage_sweeps.IV.SMU.built_in_script import get_data, run

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class IvSweepProcedure(Procedure):
    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    top_channel = IntegerParameter("Top channel", default=4)
    bottom_channel = IntegerParameter("Bottom channel", default=3)
    average = IntegerParameter("Intergration coefficient", default=127, minimum=1, maximum=127)
    advanced_config = BooleanParameter("Advanced config", default=False)
    steps = IntegerParameter("Steps", default=100, group_by="advanced_config")
    compliance = FloatParameter("Current compliance", units="A", default=0.001, group_by="advanced_config")

    DATA_COLUMNS = ["Voltage", "Top electrode current", "Time"]

    def startup(self):
        self.b1500 = connect_instrument(timeout=60000, reset=True)

    def execute(self):
        log.info(f"Starting the {self.__class__}")

        run(
            self.b1500,
            self.first_voltage,
            self.second_voltage,
            self.steps,
            top=self.top_channel,
            current_comp=self.compliance,
            average=self.average,
        )
        times, voltages, currents = get_data(self.b1500)
        print(f"len(times) = {len(times), len(voltages), len(currents)}")
        print(voltages[:20])

        self.emit(
            "batch results",
            {"Time": times, "Voltage": voltages, "Top electrode current": np.abs(currents)},
        )

        self.b1500.force_gnd()


class MainWindow(ManagedWindowBase):
    def __init__(self):
        widget_list = (
            PlotWidget("Results Graph", IvSweepProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        settings = [
            "first_voltage",
            "second_voltage",
            "top_channel",
            "bottom_channel",
            "average",
            "advanced_config",
            "steps",
            "compliance",
        ]
        super().__init__(
            procedure_class=IvSweepProcedure,
            inputs=settings,
            displays=settings,
            widget_list=widget_list,
        )
        logging.getLogger().addHandler(widget_list[1].handler)
        log.setLevel(self.log_level)
        log.info("ManagedWindow connected to logging")
        self.setWindowTitle(f"{self.procedure_class.__name__}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
