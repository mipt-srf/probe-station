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

from probe_station.measurements.common import connect_instrument

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def parse(string):
    value_strings = string.split(",")
    values = [float(value_str[3:]) for value_str in value_strings]
    return values


class RandomProcedure(Procedure):
    source = IntegerParameter("Source channel", default=4)
    drain = IntegerParameter("Drain channel", default=3)
    gate = IntegerParameter("Gate channel", default=1)

    voltage_ds = FloatParameter("Drain-source voltage", units="V", default=1.0)
    voltage_gate_first = FloatParameter("Gate voltage (first)", units="V", default=-20.0)
    voltage_gate_second = FloatParameter("Gate voltage (second)", units="V", default=20.0)
    points = IntegerParameter("Points per sweep", default=100)

    DATA_COLUMNS = ["Gate Voltage", "Drain-Source Current", "Gate Current"]

    def startup(self):
        self.b1500 = connect_instrument()

    def execute(self):
        self.smu_source = self.b1500.smus[self.source]
        self.smu_source.enable()
        self.smu_drain = self.b1500.smus[self.drain]
        self.smu_drain.enable()
        self.smu_gate = self.b1500.smus[self.gate]
        self.smu_gate.enable()

        self.b1500.clear_timer()

        voltages = np.concatenate(
            (
                np.linspace(0, self.voltage_gate_first, self.points // 3),
                np.linspace(self.voltage_gate_first, self.voltage_gate_second, self.points // 3),
                np.linspace(self.voltage_gate_second, 0, self.points // 3),
            ),
        )
        if self.smu_source.name.endswith("3") or self.smu_source.name.endswith("4"):
            if abs(self.voltage_ds) <= 20:
                compliance = 100e-3
            elif 20 < abs(self.voltage_ds) <= 40:
                compliance = 50e-3
            elif 40 < abs(self.voltage_ds) <= 100:
                compliance = 20e-3
            else:
                raise ValueError(f"Voltages higher than 100 V are not suported by {self.smu_source.name}")


        self.smu_source.force("voltage", 0, self.voltage_ds, compliance)
        for voltage in voltages:

            if self.smu_gate.name.endswith("1"):
                if max(abs(self.voltage_gate_first), abs(self.voltage_gate_second)) > 100:
                    gate_compliance = 50e-3
                else:
                    gate_compliance = 125e-3
            self.smu_gate.force("voltage", 0, voltage, gate_compliance)  # 4 ms between steps, 10 ms with measuring
            time, current, voltage_meas = parse(self.b1500.ask(f"TTIV {self.smu_source.channel}, 0, 0"))
            # sleep(0.05)
            # time, gate_current, voltage_meas = parse(
            #     self.b1500.ask(f"TTIV {self.smu_gate.name[-1]}, 15, 0")
            # )
            data = {
                "Gate Voltage": voltage,
                "Drain-Source Current": np.abs(current),
                # "Gate Current": gate_current,
            }
            self.emit("results", data)
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break

        self.smu_source.force("voltage", 0, 0)
        self.smu_gate.force("voltage", 0, 0)


class MainWindow(ManagedWindowBase):
    def __init__(self):
        widget_list = (
            PlotWidget("Results Graph", RandomProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=RandomProcedure,
            inputs=[
                "source",
                "drain",
                "gate",
                "voltage_ds",
                "voltage_gate_first",
                "voltage_gate_second",
                "points",
            ],
            displays=[
                "source",
                "drain",
                "gate",
                "voltage_ds",
                "voltage_gate_first",
                "voltage_gate_second",
                "points",
            ],
            widget_list=widget_list,
        )
        logging.getLogger().addHandler(widget_list[1].handler)
        log.setLevel(self.log_level)
        log.info("ManagedWindow connected to logging")
        self.setWindowTitle("Ids (Vg)")
        self.filename = "voltage_ds={Drain-source voltage}"


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
