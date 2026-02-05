import logging
import sys

import numpy as np
from keysight_b1530a._bindings.initialization import open_session
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
    Procedure,
)
from PyQt5.QtCore import QLocale

from probe_station.measurements.common import (
    RSU,
    RSUOutputMode,
    connect_instrument,
    get_smu_by_number,
    setup_rsu_output,
)
from probe_station.measurements.voltage_sweeps.IV.SMU.script import measure_at_voltage

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class IvSweepProcedure(Procedure):
    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    top_channel = IntegerParameter("Top channel", default=4)
    bottom_channel = IntegerParameter("Bottom channel", default=3)
    steps = IntegerParameter("Steps", default=100)

    DATA_COLUMNS = ["Time", "Voltage", "Top electrode current"]

    def startup(self):
        self.b1500 = connect_instrument(timeout=10000)
        open_session()
        # self.b1500.reset()

    def execute(self):
        log.info(f"Starting the {self.__class__}")

        setup_rsu_output(self.b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
        setup_rsu_output(self.b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

        top_smu = get_smu_by_number(self.b1500, self.top_channel)
        bottom_smu = get_smu_by_number(self.b1500, self.bottom_channel)

        top_smu.enable()
        bottom_smu.enable()

        top_smu.force("voltage", 0, 0)
        bottom_smu.force("voltage", 0, 0)

        voltages_forced = np.linspace(self.first_voltage, self.second_voltage, self.steps)

        for i, voltage in enumerate(voltages_forced):
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                self.b1500.abort()
                self.b1500.force_gnd()
                return

            self.emit("progress", i / self.steps * 100)
            time, current, voltage = measure_at_voltage(
                self.b1500, voltage, top=self.top_channel, bottom=self.bottom_channel
            )
            self.emit("results", {"Time": time, "Voltage": voltage, "Top electrode current": np.abs(current)})

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
            "steps",
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
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
