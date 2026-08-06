import logging
from typing import ClassVar

import numpy as np
from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.b1500 import RSUOutputMode
from probe_station.measurements.b1500_helpers import max_compliance
from probe_station.measurements.pymeasure_base import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.session import Session
from probe_station.measurements.smu._widgets import IvPlotWidget
from probe_station.measurements.smu.iv_step_runner import measure_at_voltage

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SmuIvStepProcedure(BaseProcedure):
    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    top_channel = IntegerParameter("Top channel", default=4)
    bottom_channel = IntegerParameter("Bottom channel", default=3)
    steps = IntegerParameter("Steps", default=100)

    DATA_COLUMNS: ClassVar[list[str]] = ["Time", "Voltage", "Top Electrode Current"]

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire(timeout=10000)
        # self.b1500.reset()

    def execute(self):
        logger.info(f"Starting the {self.__class__}")

        self.b1500.rsus[1].set_output(RSUOutputMode.SMU)
        self.b1500.rsus[2].set_output(RSUOutputMode.SMU)

        top_smu = self.b1500.smus[self.top_channel]
        bottom_smu = self.b1500.smus[self.bottom_channel]

        top_smu.enable()
        bottom_smu.enable()

        peak = max(abs(self.first_voltage), abs(self.second_voltage))
        top_smu.force("voltage", 0, 0, max_compliance(top_smu, peak))
        bottom_smu.force("voltage", 0, 0, max_compliance(bottom_smu, 0))

        voltages_forced = np.linspace(self.first_voltage, self.second_voltage, self.steps)

        for i, voltage in enumerate(voltages_forced):
            if self.should_stop():
                logger.warning("Caught the stop flag in the procedure")
                self.b1500.abort()
                self.b1500.force_gnd()
                Session.close()
                return

            self.emit("progress", i / self.steps * 100)
            time, current, voltage = measure_at_voltage(
                self.b1500, voltage, top=self.top_channel, bottom=self.bottom_channel
            )
            self.emit("results", {"Time": time, "Voltage": voltage, "Top Electrode Current": current})

        self.b1500.force_gnd()


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            IvPlotWidget("Results Graph", SmuIvStepProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=SmuIvStepProcedure,
            widget_list=widget_list,
            logger=logger,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
