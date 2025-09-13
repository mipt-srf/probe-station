import logging
import sys

import numpy as np
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter, Procedure

from probe_station.measurements.common import connect_instrument, get_smu_by_number
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
        self.b1500 = connect_instrument(timeout=60000)
        # self.b1500.reset()

    def execute(self):
        log.info(f"Starting the {self.__class__}")

        top_smu = get_smu_by_number(self.b1500, self.top_channel)
        bottom_smu = get_smu_by_number(self.b1500, self.bottom_channel)

        top_smu.enable()
        bottom_smu.enable()

        top_smu.force("voltage", 0, 0)
        bottom_smu.force("voltage", 0, 0)

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

        self.emit("batch results", {"Time": times, "Voltage": voltages, "Top electrode current": np.abs(currents)})

        # self.emit("progress", i / self.steps * 100)
        # time, current, voltage = measure_at_voltage(
        #     self.b1500, voltage, top=self.top_channel, bottom=self.bottom_channel
        # )
        # self.emit("results", {"Time": time, "Voltage": voltage, "Top electrode current": np.abs(current)})
        # # sleep(0.01)

        self.b1500.force_gnd()

        # sec_per_step = 0.034
        # for i in range(100):
        #     sleep(sec_per_step * self.steps / 100)
        #     self.emit("progress", i)
        #     if self.should_stop():
        #         log.warning("Caught the stop flag in the procedure")
        #         self.b1500.abort()
        #         self.b1500.force_gnd()
        #         break
        # else:
        #     capacitance, resistance, ac, dc_measured, dc_forced = get_results(self.b1500)
        #     self.emit(
        #         "batch results",
        #         {
        #             "Voltage": dc_measured,
        #             "Top electrode current": capacitance,
        #         },
        #     )


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
