"""PyMeasure procedure for applying a DC voltage for a fixed duration."""

import logging
from time import sleep

from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
)

from probe_station.measurements.common import (
    RSU,
    BaseProcedure,
    BaseWindow,
    RSUOutputMode,
    get_smu_by_number,
    max_compliance,
    run_app,
    setup_rsu_output,
)
from probe_station.measurements.session import Session

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SmuDcVoltageProcedure(BaseProcedure):
    """Apply a constant DC voltage on a selected SMU channel for a given duration."""

    voltage = FloatParameter("Voltage", units="V", default=10.0)
    time = FloatParameter("Time", units="s", default=1, minimum=0.2)
    channel = IntegerParameter("Channel", default=4)

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire()
        setup_rsu_output(self.b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
        setup_rsu_output(self.b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    def execute(self):
        log.info(f"Starting the {self.__class__}")

        top_smu = get_smu_by_number(self.b1500, self.channel)
        top_smu.enable()
        top_smu.force("voltage", 0, self.voltage, max_compliance(top_smu, abs(self.voltage)))
        self.time -= 0.1  # compensation for the time spent on commands
        for i in range(100):
            sleep(self.time / 100)
            self.emit("progress", i + 1)
        top_smu.force("voltage", 0, 0)


class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__(
            procedure_class=SmuDcVoltageProcedure,
            logger=log,
        )


if __name__ == "__main__":
    run_app(MainWindow)
