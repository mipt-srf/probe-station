import logging
import sys

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter
from qtpy.QtCore import QLocale

from probe_station.measurements.common import BaseProcedure, BaseWindow, connect_instrument
from probe_station.measurements.voltage_sweeps.IV.SMU.built_in_script import run
from probe_station.measurements.voltage_sweeps.IV.widgets import IvPlotWidget
from probe_station.utilities import setup_file_logging

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
            total_steps = 2 * self.steps - 1
        else:
            total_steps = 2 * self.steps

        for emitted, (time, current, voltage) in enumerate(self.b1500.iter_output(total_steps, 3), start=1):
            self.emit("progress", emitted / total_steps * 100)
            self.emit(
                "results",
                {"Time": time, "Voltage": voltage, "Top electrode current": current},
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
            IvPlotWidget("Results Graph", IvSweepProcedure.DATA_COLUMNS),
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
            logger=log,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
