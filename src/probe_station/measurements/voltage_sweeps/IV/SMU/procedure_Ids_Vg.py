import logging
import sys

import numpy as np
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
)
from qtpy.QtCore import QLocale

from probe_station.measurements.common import (
    BaseProcedure,
    BaseWindow,
    connect_instrument,
    get_smu_by_number,
    max_compliance,
)
from probe_station.measurements.voltage_sweeps.IV.widgets import IvPlotWidget
from probe_station.utilities import setup_file_logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# TODO: replace with parse_data from common
def parse(string):
    value_strings = string.split(",")
    values = [float(value_str[3:]) for value_str in value_strings]
    return values


class RandomProcedure(BaseProcedure):
    source = IntegerParameter("Source channel", default=4)
    drain = IntegerParameter("Drain channel", default=3)
    gate = IntegerParameter("Gate channel", default=1)

    voltage_ds = FloatParameter("Drain-source voltage", units="V", default=1.0)
    voltage_gate_first = FloatParameter("Gate voltage (first)", units="V", default=-20.0)
    voltage_gate_second = FloatParameter("Gate voltage (second)", units="V", default=20.0)
    points = IntegerParameter("Points per sweep", default=100)

    DATA_COLUMNS = ["Gate Voltage", "Drain-Source Current", "Gate Current"]

    def startup(self):
        super().startup()
        self.b1500 = connect_instrument()

    def execute(self):
        # self.smu_source = self.b1500.smus[self.source]
        self.smu_source = get_smu_by_number(self.b1500, self.source)  # temp fix, while SMU rework is not merged
        self.smu_source.enable()

        # self.smu_drain = self.b1500.smus[self.drain]
        self.smu_drain = get_smu_by_number(self.b1500, self.drain)  # temp fix, while SMU rework is not merged
        self.smu_drain.enable()

        # self.smu_gate = self.b1500.smus[self.gate]
        self.smu_gate = get_smu_by_number(self.b1500, self.gate)  # temp fix, while SMU rework is not merged
        self.smu_gate.enable()

        self.b1500.clear_timer()

        voltages = np.concatenate(
            (
                np.linspace(0, self.voltage_gate_first, self.points // 3),
                np.linspace(self.voltage_gate_first, self.voltage_gate_second, self.points // 3),
                np.linspace(self.voltage_gate_second, 0, self.points // 3),
            ),
        )
        self.smu_source.force("voltage", 0, self.voltage_ds, max_compliance(self.smu_source, abs(self.voltage_ds)))
        gate_peak = max(abs(self.voltage_gate_first), abs(self.voltage_gate_second))
        self.smu_gate.force("voltage", 0, 0, max_compliance(self.smu_gate, gate_peak))
        for voltage in voltages:
            self.smu_gate.force("voltage", 0, voltage)  # 4 ms between steps, 10 ms with measuring
            time, current, voltage_meas = parse(self.b1500.ask(f"TTIV {self.smu_source.channel}, 0, 0"))
            # sleep(0.05)
            # time, gate_current, voltage_meas = parse(
            #     self.b1500.ask(f"TTIV {self.smu_gate.name[-1]}, 15, 0")
            # )
            data = {
                "Gate Voltage": voltage,
                "Drain-Source Current": current,
                # "Gate Current": gate_current,
            }
            self.emit("results", data)
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break

        self.smu_source.force("voltage", 0, 0)
        self.smu_gate.force("voltage", 0, 0)


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            IvPlotWidget("Results Graph", RandomProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=RandomProcedure,
            widget_list=widget_list,
            logger=log,
        )
        self.setWindowTitle("Ids (Vg)")
        self.filename = "voltage_ds={Drain-source voltage}"


if __name__ == "__main__":
    setup_file_logging("logs")
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
