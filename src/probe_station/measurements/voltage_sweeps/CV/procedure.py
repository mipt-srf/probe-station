import logging

from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.common import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.session import Session
from probe_station.measurements.voltage_sweeps.CV.script import PLOT_POINTS, run

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class CvSweepProcedure(BaseProcedure):
    """Capacitance-voltage sweep procedure using the B1500 built-in CV measurement."""

    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    avg_per_point = IntegerParameter("Averages per point", default=1)
    # channel = IntegerParameter("Channel", default=2)

    DATA_COLUMNS = ["Voltage", "Capacitance", "Resistance"]

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire(reset=False)

    def execute(self):
        log.info(f"Starting the {self.__class__}")

        run(
            b1500=self.b1500,
            first_bias=self.first_voltage,
            second_bias=self.second_voltage,
            avg_per_point=self.avg_per_point,
        )
        measure_points = self.avg_per_point * PLOT_POINTS
        total_steps = 2 * measure_points  # LINEAR_DOUBLE sweep: forward + backward

        for i, (_, Cp, Rp, _ac, dc_measured, _dc_forced) in enumerate(self.b1500.iter_output(total_steps, 6)):
            self.emit("progress", (i + 1) / total_steps * 100)
            self.emit("results", {"Voltage": dc_measured, "Capacitance": Cp, "Resistance": Rp})
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                self.b1500.abort()
                self.b1500.force_gnd()
                return

    # def shutdown(self):
    #     close_session()


class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__(
            procedure_class=CvSweepProcedure,
            logger=log,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
