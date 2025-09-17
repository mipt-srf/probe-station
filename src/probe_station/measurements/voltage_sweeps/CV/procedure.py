import logging
import sys
from time import sleep

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
    Procedure,
)

from probe_station.measurements.common import connect_instrument
from probe_station.measurements.voltage_sweeps.CV.script import PLOT_POINTS, get_results, run

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class CvSweepProcedure(Procedure):
    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    avg_per_point = IntegerParameter("Averages per point", default=1)
    # channel = IntegerParameter("Channel", default=2)

    DATA_COLUMNS = ["Voltage", "Capacitance", "Resistance"]

    def startup(self):
        self.b1500 = connect_instrument(reset=True)

    def execute(self):
        log.info(f"Starting the {self.__class__}")

        run(
            b1500=self.b1500,
            first_bias=self.first_voltage,
            second_bias=self.second_voltage,
            avg_per_point=self.avg_per_point,
        )
        measure_points = self.avg_per_point * PLOT_POINTS
        sec_per_point = 32 / 200
        sec_per_percent = sec_per_point * measure_points / 100
        for i in range(100):
            sleep(sec_per_percent)
            self.emit("progress", i)
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                self.b1500.abort()
                self.b1500.force_gnd()
                break
        else:
            capacitance, resistance, ac, dc_measured, dc_forced = get_results(self.b1500)
            self.emit(
                "batch results",
                {
                    "Voltage": dc_measured,
                    "Capacitance": capacitance,
                    "Resistance": resistance,
                },
            )


class MainWindow(ManagedWindowBase):
    def __init__(self):
        widget_list = (
            PlotWidget("Results Graph", CvSweepProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        settings = [
            "first_voltage",
            "second_voltage",
            "avg_per_point",
        ]
        super().__init__(
            procedure_class=CvSweepProcedure,
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
