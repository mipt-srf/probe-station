import logging
import sys

import numpy as np
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
    Procedure,
)
from pymeasure.instruments.agilent.agilentB1500 import (
    ControlMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
)

from probe_station.measurements.common import connect_instrument, get_smu_by_number
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
        # self.b1500.reset()

    def execute(self):
        log.info(f"Starting the {self.__class__}")

        self.b1500.control_mode = ControlMode.SMU_PGU_SELECTOR
        self.b1500.set_port_connection(port=PgSelectorPort.OUTPUT_2_FIRST, status=PgSelectorConnectionStatus.SMU_ON)
        self.b1500.set_port_connection(port=PgSelectorPort.OUTPUT_1_FIRST, status=PgSelectorConnectionStatus.SMU_ON)

        top_smu = get_smu_by_number(self.b1500, self.top_channel)
        bottom_smu = get_smu_by_number(self.b1500, self.bottom_channel)

        top_smu.force("voltage", 0, 0)
        bottom_smu.force("voltage", 0, 0)

        top_smu.enable()
        bottom_smu.enable()

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
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
