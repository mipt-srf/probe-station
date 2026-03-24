import logging
import sys

import numpy as np
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter
from PyQt5.QtCore import QLocale

from probe_station.measurements.common import BaseProcedure, connect_instrument
from probe_station.measurements.voltage_sweeps.IV.SMU.built_in_script import iter_sweep_data, run

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class IvSweepProcedure(BaseProcedure):
    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    top_channel = IntegerParameter("Top channel", default=4)
    bottom_channel = IntegerParameter("Bottom channel", default=3)
    average = IntegerParameter("Intergration coefficient", default=127, minimum=1, maximum=127)
    advanced_config = BooleanParameter("Advanced config", default=False)
    steps = IntegerParameter("Steps", default=100, group_by="advanced_config")
    mode = IntegerParameter("Mode", default=1, group_by="advanced_config")
    # compliance = FloatParameter("Current compliance", units="A", default=0.1, group_by="advanced_config")

    DATA_COLUMNS = ["Voltage", "Top electrode current", "Time"]

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
            top=self.top_channel,
            # current_comp=self.compliance,
            average=self.average,
            mode=self.mode,
        )

        # mode 1: one LINEAR_DOUBLE sweep → 2*steps output points
        # mode 2: two LINEAR_DOUBLE half-sweeps, each configured with steps//2 and LINEAR_DOUBLE
        if self.mode == 2:
            steps_per_sweep = 2 * (self.steps // 2)
            num_sweeps = 2
        else:
            steps_per_sweep = 2 * self.steps
            num_sweeps = 1
        total_steps = num_sweeps * steps_per_sweep

        emitted = 0
        for _ in range(num_sweeps):
            gen = iter_sweep_data(self.b1500, steps_per_sweep)
            try:
                for time, voltage, current in gen:
                    emitted += 1
                    self.emit("progress", emitted / total_steps * 100)
                    self.emit(
                        "results",
                        {"Time": time, "Voltage": voltage, "Top electrode current": np.abs(current)},
                    )
                    if self.should_stop():
                        log.warning("Caught the stop flag in the procedure")
                        self.b1500.abort()
                        self.b1500.force_gnd()
                        return
            finally:
                gen.close()


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
            "mode",
            # "compliance",
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
