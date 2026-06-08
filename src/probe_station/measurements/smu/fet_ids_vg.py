import logging

import numpy as np
from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.b1500_helpers import max_compliance, parse_data
from probe_station.measurements.pymeasure_base import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.rsu import RSU, RSUOutputMode, setup_rsu_output
from probe_station.measurements.session import Session
from probe_station.measurements.smu._widgets import IvPlotWidget

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SmuFetIdsVgProcedure(BaseProcedure):
    source = IntegerParameter("Source channel", default=4)
    drain = IntegerParameter("Drain channel", default=3)
    gate = IntegerParameter("Gate channel", default=1)
    base = IntegerParameter("Base channel", default=2)

    voltage_ds = FloatParameter("Drain-source voltage", units="V", default=1.0)
    voltage_gate_first = FloatParameter("Gate voltage (first)", units="V", default=-20.0)
    voltage_gate_second = FloatParameter("Gate voltage (second)", units="V", default=20.0)
    points = IntegerParameter("Points per sweep", default=100)

    DATA_COLUMNS = ["Gate Voltage", "Drain-Source Current", "Gate Current"]

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire()
        self.b1500.clear_buffer()
        setup_rsu_output(self.b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
        setup_rsu_output(self.b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    def execute(self):
        self.smu_source = self.b1500.smus[self.source]
        self.smu_source.enable()
        self.smu_source.force("voltage", 0, 0, max_compliance(self.smu_source, 0))

        self.smu_drain = self.b1500.smus[self.drain]
        self.smu_drain.enable()

        self.smu_gate = self.b1500.smus[self.gate]
        self.smu_gate.enable()

        self.smu_base = self.b1500.smus[self.base]
        self.smu_base.enable()
        self.smu_base.force("voltage", 0, 0, max_compliance(self.smu_base, 0))

        self.b1500.clear_timer()

        voltages = np.concatenate(
            (
                np.linspace(0, self.voltage_gate_first, self.points // 3),
                np.linspace(self.voltage_gate_first, self.voltage_gate_second, self.points // 3),
                np.linspace(self.voltage_gate_second, 0, self.points // 3),
            ),
        )
        self.smu_drain.force("voltage", 0, self.voltage_ds, max_compliance(self.smu_drain, abs(self.voltage_ds)))
        gate_peak = max(abs(self.voltage_gate_first), abs(self.voltage_gate_second))
        self.smu_gate.force("voltage", 0, 0, max_compliance(self.smu_gate, gate_peak))
        for voltage in voltages:
            self.smu_gate.force("voltage", 0, voltage)  # 4 ms between steps, 10 ms with measuring
            time, current, voltage_meas = parse_data(self.b1500.ask(f"TTIV {self.smu_drain.channel}, 0, 0"))
            # sleep(0.05)
            # time, gate_current, voltage_meas = parse_data(
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
                self.b1500.abort()
                self.b1500.force_gnd()
                break

        self.smu_drain.force("voltage", 0, 0)
        self.smu_gate.force("voltage", 0, 0)
        self.smu_base.force("voltage", 0, 0)


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
        self.filename = "voltage_ds={Drain-source voltage}"


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
