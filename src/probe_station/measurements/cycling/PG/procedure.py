import logging
import sys
from datetime import datetime, timedelta

from keysight_b1530a._bindings.initialization import open_session
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter, Metadata, Procedure

from probe_station.measurements.cycling.PG.script import connect_instrument, run

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class PgCyclingProcedure(Procedure):
    repetitions = IntegerParameter("Number of cycles", default=10, maximum=2147483647)
    amplitude = FloatParameter("Pulse amplitude", units="V", default=10.0)
    width = FloatParameter("Pulse width", units="s", default=0.1)
    rise = FloatParameter("Pulse rise time", units="s", default=100e-9)
    tail = FloatParameter("Pulse tail time", units="s", default=100e-9)
    channel = IntegerParameter("Channel", default=2)
    bipolar_pulses = BooleanParameter("Bipolar Pulses", default=False)
    pulse_separation = BooleanParameter("Pulse separation", default=True)

    dc_bias = BooleanParameter("Enable DC bias", default=False)
    dc_channel = IntegerParameter("DC bias channel", default=1, group_by="dc_bias")
    dc_bias_value = FloatParameter("DC bias", default=0.0, group_by="dc_bias")

    start_time = Metadata("Start time", default=0)

    DATA_COLUMNS = ["Cycle", "Random Number"]

    def startup(self):
        self.b1500 = connect_instrument()
        open_session()
        self.start_time = datetime.now()

    def execute(self):
        log.info("Starting the loop of %d repetitions" % self.repetitions)

        if self.dc_bias:
            dc_smu = None

            for smu in self.b1500.smu_references:
                if str(self.dc_channel) == smu.name[-1]:
                    dc_smu = smu
            dc_smu.enable()
            dc_smu.force("voltage", 0, self.dc_bias_value)

            log.info("Starting output of %f V at %d", self.dc_bias_value, self.dc_channel)

        run(
            b1500=self.b1500,
            repetitions=self.repetitions,
            amplitude=self.amplitude,
            width=self.width,
            rise=self.rise,
            tail=self.tail,
            channel=self.channel + 100,
            bipolar=self.bipolar_pulses,
            pulse_separation=self.pulse_separation,
        )

        if self.dc_bias:
            dc_smu.force_gnd()

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


class MainWindow(ManagedWindowBase):
    def __init__(self):
        widget_list = (LogWidget("Experiment Log"),)
        settings = [
            "repetitions",
            "amplitude",
            "width",
            "rise",
            "tail",
            "channel",
            "bipolar_pulses",
            "pulse_separation",
            "dc_bias",
            "dc_bias_value",
            "dc_channel",
        ]
        super().__init__(
            procedure_class=PgCyclingProcedure,
            inputs=settings,
            displays=settings,
            widget_list=widget_list,
        )
        logging.getLogger().addHandler(widget_list[0].handler)
        log.setLevel(self.log_level)
        log.info("ManagedWindow connected to logging")
        self.filename = "width={Pulse width}_num={Number of cycles}_ampl={Pulse amplitude:.0f}"
        self.setWindowTitle("GUI Example")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
