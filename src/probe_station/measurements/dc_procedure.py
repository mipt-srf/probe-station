import logging
import sys
from time import sleep

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
    Procedure,
)
from PyQt5.QtCore import QLocale

from probe_station.measurements.common import (
    RSU,
    RSUOutputMode,
    connect_instrument,
    get_smu_by_number,
    setup_rsu_output,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class DcProcedure(Procedure):
    voltage = FloatParameter("Voltage", units="V", default=10.0)
    time = FloatParameter("Time", units="s", default=1, minimum=0.2)
    channel = IntegerParameter("Channel", default=4)

    DATA_COLUMNS = []

    def startup(self):
        self.b1500 = connect_instrument()
        setup_rsu_output(self.b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
        setup_rsu_output(self.b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    def execute(self):
        log.info(f"Starting the {self.__class__}")

        top_smu = get_smu_by_number(self.b1500, self.channel)
        top_smu.enable()
        top_smu.force("voltage", 0, self.voltage)
        self.time -= 0.1  # compensation for the time spent on commands
        for i in range(100):
            sleep(self.time / 100)
            self.emit("progress", i + 1)
        top_smu.force("voltage", 0, 0)

class MainWindow(ManagedWindowBase):
    def __init__(self):
        widget_list = (LogWidget("Experiment Log"),)
        settings = [
            "voltage",
            "time",
            "channel",
        ]
        super().__init__(
            procedure_class=DcProcedure,
            inputs=settings,
            displays=settings,
            widget_list=widget_list,
        )
        logging.getLogger().addHandler(widget_list[0].handler)
        log.setLevel(self.log_level)
        log.info("ManagedWindow connected to logging")
        self.setWindowTitle(self.procedure_class.__name__)


if __name__ == "__main__":
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
