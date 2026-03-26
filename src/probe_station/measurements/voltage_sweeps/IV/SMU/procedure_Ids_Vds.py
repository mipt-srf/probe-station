import logging
import sys

import numpy as np
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter
from PyQt5.QtCore import QLocale

from probe_station.measurements.common import BaseProcedure, connect_instrument
from probe_station.measurements.voltage_sweeps.IV.SMU.script_Ids_Vds import get_data, run

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class IvSweepProcedure(BaseProcedure):
    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    vg_start = FloatParameter("Vg start", units="V", default=-20)
    vg_stop = FloatParameter("Vg stop", units="V", default=20)
    vg_steps = IntegerParameter("Vg steps", default=5, minimum=1)
    source_channel = IntegerParameter("Source channel", default=4)
    drain_channel = IntegerParameter("Drain channel", default=3)
    gate_channel = IntegerParameter("Gate channel", default=1)
    average = IntegerParameter("Intergration coefficient", default=127, minimum=1, maximum=127)
    advanced_config = BooleanParameter("Advanced config", default=False)
    steps = IntegerParameter("Steps", default=100, group_by="advanced_config")
    mode = IntegerParameter("Mode", default=1, group_by="advanced_config")

    DATA_COLUMNS = ["Vg", "Voltage", "Source electrode current", "Time"]

    def startup(self):
        super().startup()
        self.b1500 = connect_instrument(timeout=60000, reset=False)

    def execute(self):
        log.info(f"Starting the {self.__class__}")

        vg_values = np.linspace(self.vg_start, self.vg_stop, self.vg_steps)
        for vg in vg_values:
            run(
                self.b1500,
                self.first_voltage,
                self.second_voltage,
                self.steps,
                average=self.average,
                top=self.source_channel,
                bottom=self.drain_channel,
                mode=self.mode,
                gate=self.gate_channel,
                gate_voltage=vg,
            )
            times, voltages, currents = get_data(self.b1500)
            self.emit(
                "batch results",
                {
                    "Vg": np.full(len(voltages), vg),
                    "Voltage": voltages,
                    "Source electrode current": np.abs(currents),
                    "Time": times,
                },
            )


class MainWindow(ManagedWindowBase):
    def __init__(self):
        widget_list = (
            PlotWidget("Results Graph", IvSweepProcedure.DATA_COLUMNS, x_axis="Voltage"),
            LogWidget("Experiment Log"),
        )
        settings = [
            "first_voltage",
            "second_voltage",
            "vg_start",
            "vg_stop",
            "vg_steps",
            "source_channel",
            "drain_channel",
            "gate_channel",
            "average",
            "advanced_config",
            "steps",
            "mode",
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
        self.setWindowTitle("Ids (Vg, Vds)")


if __name__ == "__main__":
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
