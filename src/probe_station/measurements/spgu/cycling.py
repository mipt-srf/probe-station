import logging
from datetime import datetime, timedelta
from typing import cast

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.b1500_helpers import max_compliance
from probe_station.measurements.pymeasure_base import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.session import Session
from probe_station.measurements.spgu.cycling_runner import run

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SpguCyclingProcedure(BaseProcedure):
    """Pulse-generator cycling procedure for fatigue/wake-up experiments.

    Sends bipolar or unipolar voltage pulses via the B1500 SPGU and
    records cycle count metadata.
    """

    # Parameters are annotated with their runtime value types: pymeasure replaces
    # the Parameter attributes with plain values on procedure instances.
    repetitions: int = cast("int", IntegerParameter("Number of cycles", default=10, maximum=2147483647))
    amplitude: float = cast("float", FloatParameter("Pulse amplitude", units="V", default=10.0))
    width: float = cast("float", FloatParameter("Pulse width", units="s", default=0.1))
    rise: float = cast("float", FloatParameter("Pulse rise time", units="s", default=100e-9))
    tail: float = cast("float", FloatParameter("Pulse tail time", units="s", default=100e-9))
    channel: int = cast("int", IntegerParameter("Channel", default=2))
    bipolar_pulses: bool = cast("bool", BooleanParameter("Bipolar Pulses", default=False))
    pulse_separation: bool = cast("bool", BooleanParameter("Pulse separation", default=True))

    dc_bias: bool = cast("bool", BooleanParameter("Enable DC bias", default=False))
    dc_bias_value: float = cast("float", FloatParameter("DC bias", default=0.0, group_by="dc_bias"))
    dc_channel: int = cast("int", IntegerParameter("DC bias channel", default=1, group_by="dc_bias"))

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire()

    def execute(self):
        logger.info("Starting the loop of %d repetitions" % self.repetitions)

        if self.dc_bias:
            dc_smu = None

            for smu in self.b1500.smu_references:
                if str(self.dc_channel) == smu.name[-1]:
                    dc_smu = smu
            if dc_smu is None:
                raise ValueError(f"No SMU found for DC bias channel {self.dc_channel}")
            dc_smu.enable()
            dc_smu.force("voltage", 0, self.dc_bias_value, max_compliance(dc_smu, abs(self.dc_bias_value)))

            logger.info("Starting output of %f V at %d", self.dc_bias_value, self.dc_channel)

        try:
            run(
                b1500=self.b1500,
                repetitions=self.repetitions,
                amplitude=self.amplitude,
                width=self.width,
                rise=self.rise,
                tail=self.tail,
                channel=self.channel + 100 if self.channel < 10 else self.channel,
                bipolar=self.bipolar_pulses,
                pulse_separation=self.pulse_separation,
                should_stop=self.should_stop,
            )
        finally:
            # Always drop the DC bias so a failed cycling run does not leave
            # the SMU biased on the device.
            if self.dc_bias:
                dc_smu.force("Voltage", 0, 0)

    def get_estimates(self, sequence_length=None, sequence=None):
        delay_2nd = 2 * self.width
        period = (delay_2nd + (self.rise + self.width + self.tail) * 2) + delay_2nd
        duration = self.repetitions * period

        estimates = [
            ("Duration", "%d s" % int(duration)),
            ("Number of lines", "%d" % int(self.repetitions)),
            ("Sequence length", str(sequence_length)),
            (
                "Measurement finished at",
                str(datetime.now() + timedelta(seconds=duration)),
            ),
        ]

        return estimates


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (LogWidget("Experiment Log"),)
        super().__init__(
            procedure_class=SpguCyclingProcedure,
            widget_list=widget_list,
            logger=logger,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
