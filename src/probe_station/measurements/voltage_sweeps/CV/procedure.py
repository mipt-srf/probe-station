import logging
import sys
from time import sleep

from keysight_b1530a._bindings.initialization import close_session, open_session
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
    Procedure,
)
from PyQt5.QtCore import QLocale

from probe_station.measurements.common import connect_instrument
from probe_station.measurements.voltage_sweeps.CV.script import (
    PLOT_POINTS,
    get_results,
    run,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class CvSweepProcedure(Procedure):
    """Capacitance-voltage sweep procedure using the B1500 built-in CV measurement."""

    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    avg_per_point = IntegerParameter("Averages per point", default=1)
    # channel = IntegerParameter("Channel", default=2)

    DATA_COLUMNS = ["Voltage", "Capacitance", "Resistance"]

    def startup(self):
        self.b1500 = connect_instrument(reset=False)
        open_session()

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

    # def shutdown(self):
    #     close_session()


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
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
