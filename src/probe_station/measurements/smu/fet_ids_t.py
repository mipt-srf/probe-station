"""PyMeasure procedure for measuring FET drain and gate currents at fixed bias."""

import logging

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
)
from pymeasure.instruments.agilent.agilentB1500 import ADCType

from probe_station.measurements.b1500_helpers import max_compliance
from probe_station.measurements.pymeasure_base import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.rsu import RSU, RSUOutputMode, setup_rsu_output
from probe_station.measurements.session import Session

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SmuFetIdsTimeProcedure(BaseProcedure):
    """Measure drain and gate current of a FET at specified bias voltages."""

    gate_voltage = FloatParameter("Gate voltage", units="V", default=10.0)
    drain_voltage = FloatParameter("Drain voltage", units="V", default=10.0)

    gate_channel = IntegerParameter("Gate channel", default=4)
    drain_channel = IntegerParameter("Drain channel", default=1)

    advanced_config = BooleanParameter("Advanced config", default=False)
    averaging = IntegerParameter("Averaging", default=10, minimum=1, maximum=1023, group_by="advanced_config")
    source_channel = IntegerParameter("Source channel", default=3, group_by="advanced_config")
    base_channel = IntegerParameter("Base channel", default=2, group_by="advanced_config")
    source_voltage = FloatParameter("Source voltage", units="V", default=0.0, group_by="advanced_config")
    base_voltage = FloatParameter("Base voltage", units="V", default=0.0, group_by="advanced_config")

    DATA_COLUMNS = ["Drain Current", "Gate Current"]

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire()
        # Restore a clean WGFMU state: a preceding WGFMU run leaves the
        # channels in FASTIV mode, and clear + initialize releases them back
        # to SMU control (same recovery the WGFMU procedures do in startup()).
        self.b1500.clear_wgfmu()
        self.b1500.initialize_wgfmu()
        self.b1500.clear_buffer()
        setup_rsu_output(self.b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
        setup_rsu_output(self.b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    def execute(self):
        logger.info(f"Starting the {self.__class__}")

        gate_smu = self.b1500.smus[self.gate_channel]
        drain_smu = self.b1500.smus[self.drain_channel]
        source_smu = self.b1500.smus[self.source_channel]
        base_smu = self.b1500.smus[self.base_channel]

        self.b1500.adc_averaging(self.averaging)
        drain_smu.adc_type = ADCType.HSADC

        gate_smu.enable()
        drain_smu.enable()
        source_smu.enable()
        base_smu.enable()

        try:
            gate_smu.force("voltage", 0, self.gate_voltage, max_compliance(gate_smu, abs(self.gate_voltage)))
            drain_smu.force("voltage", 0, self.drain_voltage, max_compliance(drain_smu, abs(self.drain_voltage)))
            source_smu.force("voltage", 0, self.source_voltage, max_compliance(source_smu, abs(self.source_voltage)))
            base_smu.force("voltage", 0, self.base_voltage, max_compliance(base_smu, abs(self.base_voltage)))

            tuples = drain_smu.measure_point()
            logger.debug(f"Drain SMU measurement: {tuples}")
            drain_current = tuples[1][1]

            tuples = gate_smu.measure_point()
            logger.debug(f"Gate SMU measurement: {tuples}")
            gate_current = tuples[1][1]

            logger.info(f"Drain current: {drain_current:.6e} A, Gate current: {gate_current:.6e} A")

            self.emit("results", {"Drain Current": drain_current, "Gate Current": gate_current})
        finally:
            # Always return electrodes to 0 V: a mid-measurement failure must
            # not leave the FET gate biased, which would rewrite its state.
            gate_smu.force("voltage", 0, 0)
            drain_smu.force("voltage", 0, 0)
            source_smu.force("voltage", 0, 0)
            base_smu.force("voltage", 0, 0)

    # def shutdown(self):
    #     close_session()


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (LogWidget("Experiment Log"),)
        super().__init__(
            procedure_class=SmuFetIdsTimeProcedure,
            widget_list=widget_list,
            logger=logger,
        )


if __name__ == "__main__":
    run_app(MainWindow)
