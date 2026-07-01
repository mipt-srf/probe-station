"""Keithley 2450 procedure: sample current at a fixed bias until aborted.

Unlike the PUND/DC-IV procedures, this does not run a fixed trigger-model
sweep into a finite buffer. It applies a constant bias voltage and reads a
single current point once per interval in a Python loop, emitting each point
immediately. That makes the run open-ended (it can run for tens of hours) and
crash/abort safe: every sample is written to the CSV as it is taken, so
stopping keeps all data collected so far.
"""

import logging
import time

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, Parameter

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.keithley.instrument import connect_instrument, get_smu, set_smu
from probe_station.measurements.keithley.launcher import ADDRESS
from probe_station.measurements.pymeasure_base import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.smu._widgets import IvPlotWidget

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class KeithleyCurrentTimeProcedure(BaseProcedure):
    """Measure current at a constant bias voltage, one sample per interval."""

    terminal = Parameter("Terminal", default="rear")
    bias_voltage = FloatParameter("Bias voltage", units="V", default=0.0)
    interval = FloatParameter("Sampling interval", units="s", default=1.0, minimum=0.0)
    int_time = FloatParameter("Integration time", units="s", default=2e-2)
    autorange = BooleanParameter("Autorange", default=True)
    current_range = FloatParameter(
        "Current range", units="A", default=1e-6, group_by="autorange", group_condition=False
    )
    compliance = FloatParameter("Compliance current", units="A", default=1e0)

    DATA_COLUMNS = ["Time", "Current"]

    def startup(self):
        super().startup()
        self.smu = get_smu()

    def execute(self):
        logger.info("Starting %s", self.__class__.__name__)
        self.smu.set_terminal(self.terminal)
        self.smu.raise_error()

        self.smu.setup_sense_subsystem(
            int_time=self.int_time,
            autorange=self.autorange,
            range=self.current_range,
            compl=self.compliance,
        )
        self.smu.setup_source_subsystem()
        self.smu.source_voltage = self.bias_voltage
        self.smu.enable_source()
        self.smu.raise_error()

        logger.info("Sampling current every %g s at %g V (press Abort to stop)", self.interval, self.bias_voltage)
        start = time.perf_counter()
        n = 0
        while not self.should_stop():
            current = self.smu.current
            elapsed = time.perf_counter() - start
            self.emit("results", {"Time": elapsed, "Current": current})
            n += 1
            # Schedule the next sample against an absolute target (start + n*interval)
            # rather than sleeping a fixed interval each pass, so the cadence does
            # not drift over a run that lasts hours. Sleep in short slices so Abort
            # takes effect promptly instead of after a full interval.
            target = start + n * self.interval
            while not self.should_stop():
                remaining = target - time.perf_counter()
                if remaining <= 0:
                    break
                time.sleep(min(remaining, 0.1))
        logger.info("Stopped after %d samples", n)

    def shutdown(self):
        smu = getattr(self, "smu", None)
        if smu is not None:
            try:
                smu.disable_source()
            except Exception:
                logger.exception("Failed to disable source during shutdown")
        super().shutdown()


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            IvPlotWidget("Results Graph", KeithleyCurrentTimeProcedure.DATA_COLUMNS, x_axis="Time", y_axis="Current"),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=KeithleyCurrentTimeProcedure,
            widget_list=widget_list,
            logger=logger,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    set_smu(connect_instrument(ADDRESS))
    run_app(MainWindow)
