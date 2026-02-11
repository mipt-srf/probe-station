"""PyMeasure procedure for measuring FET drain and gate currents at fixed bias."""

import logging
import sys

from keysight_b1530a._bindings.initialization import open_session
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    Procedure,
)
from pymeasure.instruments.agilent.agilentB1500 import ADCType
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


class FetCurrentMeasurementProcedure(Procedure):
    """Measure drain and gate current of a FET at specified bias voltages."""

    gate_voltage = FloatParameter("Gate voltage", units="V", default=10.0)
    drain_voltage = FloatParameter("Drain voltage", units="V", default=10.0)
    source_voltage = FloatParameter("Source voltage", units="V", default=0.0, group_by="advanced_config")
    base_voltage = FloatParameter("Base voltage", units="V", default=0.0, group_by="advanced_config")

    gate_channel = IntegerParameter("Gate Channel", default=4)
    drain_channel = IntegerParameter("Drain Channel", default=3)
    source_channel = IntegerParameter("Source Channel", default=2, group_by="advanced_config")
    base_channel = IntegerParameter("Base Channel", default=1, group_by="advanced_config")

    advanced_config = BooleanParameter("Advanced config", default=False)
    averaging = IntegerParameter("Averaging", default=1023, minimum=1, maximum=1023, group_by="advanced_config")

    DATA_COLUMNS = ["Drain Current", "Gate Current"]

    def startup(self):
        self.b1500 = connect_instrument()
        open_session()
        setup_rsu_output(self.b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
        setup_rsu_output(self.b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    def execute(self):
        log.info(f"Starting the {self.__class__}")

        gate_smu = get_smu_by_number(self.b1500, self.gate_channel)
        drain_smu = get_smu_by_number(self.b1500, self.drain_channel)
        source_smu = get_smu_by_number(self.b1500, self.source_channel)
        base_smu = get_smu_by_number(self.b1500, self.base_channel)

        self.b1500.adc_averaging = self.averaging
        drain_smu.adc_type = ADCType.HSADC

        gate_smu.enable()
        drain_smu.enable()
        source_smu.enable()
        base_smu.enable()

        gate_smu.force("voltage", 0, self.gate_voltage)
        drain_smu.force("voltage", 0, self.drain_voltage)
        source_smu.force("voltage", 0, self.source_voltage)
        base_smu.force("voltage", 0, self.base_voltage)

        tuples = drain_smu.measure_point()
        print(tuples)
        drain_current = tuples[1][1]

        tuples = gate_smu.measure_point()
        print(tuples)
        gate_current = tuples[1][1]

        self.emit("results", {"Drain Current": drain_current, "Gate Current": gate_current})

        gate_smu.force("voltage", 0, 0)
        drain_smu.force("voltage", 0, 0)
        source_smu.force("voltage", 0, 0)
        base_smu.force("voltage", 0, 0)

    # def shutdown(self):
    #     close_session()


class MainWindow(ManagedWindowBase):
    def __init__(self):
        widget_list = (LogWidget("Experiment Log"),)
        settings = [
            "gate_voltage",
            "drain_voltage",
            "gate_channel",
            "drain_channel",
            "advanced_config",
            "averaging",
            "source_channel",
            "base_channel",
            "source_voltage",
            "base_voltage",
        ]
        super().__init__(
            procedure_class=FetCurrentMeasurementProcedure,
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
