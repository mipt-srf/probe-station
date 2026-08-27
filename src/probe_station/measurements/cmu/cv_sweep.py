import logging
from typing import ClassVar

from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.b1500_helpers import to_cp_rp
from probe_station.measurements.cmu.cv_sweep_runner import PLOT_POINTS, run
from probe_station.measurements.pymeasure_base import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.session import Session

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class CmuCvSweepProcedure(BaseProcedure):
    """Capacitance-voltage sweep procedure using the B1500 built-in CV measurement."""

    first_voltage = FloatParameter("First voltage", units="V", default=-3, minimum=-100, maximum=100, step=0.1)
    second_voltage = FloatParameter("Second voltage", units="V", default=3, minimum=-100, maximum=100, step=0.1)
    # CMU AC oscillator level (RMS) and frequency used during the capacitance
    # measurement.
    ac_voltage = FloatParameter("AC voltage", units="V", default=0.1, minimum=0, maximum=0.25, step=0.01)
    frequency = FloatParameter("Frequency", units="Hz", default=1e4, minimum=1e3, maximum=5e6, step=10, step_type="log")
    # CMU native averaging coefficient (ACT auto mode): samples averaged per
    # point = avg_per_point * initial averaging. 1 = no extra averaging.
    avg_per_point = IntegerParameter("Averages per point", default=1, minimum=1, maximum=1023, step=10)
    # channel = IntegerParameter("Channel", default=2)

    DATA_COLUMNS: ClassVar[list[str]] = ["Voltage", "Capacitance", "Resistance"]

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire(reset=False)
        self.b1500.clear_buffer()

    def execute(self):
        logger.info(f"Starting the {self.__class__}")

        run(
            b1500=self.b1500,
            first_bias=self.first_voltage,
            second_bias=self.second_voltage,
            avg_per_point=self.avg_per_point,
            ac_voltage=self.ac_voltage,
            frequency=self.frequency,
        )
        total_steps = 2 * PLOT_POINTS  # LINEAR_DOUBLE sweep: forward + backward

        # Per step, the 6 values are: time, the impedance pair, AC level,
        # measured DC bias and forced DC bias. Which pair the CMU returns
        # depends on the data format, so it is read as records and converted.
        for i, records in enumerate(self.b1500.iter_records(total_steps, 6)):
            Cp, Rp = to_cp_rp(records[1:3], self.frequency)
            dc_measured = records[4][3]
            self.emit("progress", (i + 1) / total_steps * 100)
            self.emit("results", {"Voltage": dc_measured, "Capacitance": Cp, "Resistance": Rp})
            if self.should_stop():
                logger.warning("Caught the stop flag in the procedure")
                self.b1500.abort()
                self.b1500.force_gnd()
                return

    # def shutdown(self):
    #     close_session()


class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__(
            procedure_class=CmuCvSweepProcedure,
            logger=logger,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
