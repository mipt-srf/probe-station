import logging
import sys
from datetime import datetime, timedelta

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter
from qtpy.QtCore import QLocale

from probe_station.measurements.common import BaseProcedure, BaseWindow, connect_instrument
from probe_station.measurements.voltage_sweeps.IV.pg_with_current_measurement import run
from probe_station.utilities import setup_file_logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class PgCyclingProcedure(BaseProcedure):
    """Pulse-generator cycling procedure for fatigue/wake-up experiments.

    Sends bipolar or unipolar voltage pulses via the B1500 SPGU and
    records cycle count metadata.
    """

    repetitions = IntegerParameter("Number of cycles", default=10, maximum=2147483647)
    amplitude = FloatParameter("Pulse amplitude", units="V", default=3.0)
    rise = FloatParameter("Pulse rise time", units="s", default=5e-2)
    tail = FloatParameter("Pulse tail time", units="s", default=5e-2)
    channel = IntegerParameter("Channel", default=2)
    bipolar_pulses = BooleanParameter("Bipolar Pulses", default=True)

    period = 2 * (rise.value + tail.value)

    DATA_COLUMNS = ["Time", "Top electrode current"]

    def startup(self):
        super().startup()
        self.b1500 = connect_instrument()

    def execute(self):
        log.info("Starting the loop of %d repetitions" % self.repetitions)

        run(
            b1500=self.b1500,
            repetitions=self.repetitions,
            amplitude=self.amplitude,
            rise=self.rise,
            tail=self.tail,
            channel=self.channel + 100 if self.channel < 10 else self.channel,
            bipolar=self.bipolar_pulses,
        )

        points = int(self.period * self.repetitions / 2e-3)
        for emitted, (index, time, current) in enumerate(self.b1500.iter_output(points, 3), start=1):
            self.emit("progress", emitted / points * 100)
            self.emit(
                "results",
                {"Time": time, "Top electrode current": current},
            )
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                self.b1500.abort()
                self.b1500.force_gnd()
                return

        self.b1500.close_wgfmu_session()

    def get_estimates(self, sequence_length=None, sequence=None):
        duration = self.repetitions * self.period

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
        widget_list = (PlotWidget("Results Graph", PgCyclingProcedure.DATA_COLUMNS), LogWidget("Experiment Log"))
        super().__init__(
            procedure_class=PgCyclingProcedure,
            widget_list=widget_list,
            logger=log,
        )
        self.filename = "width={Pulse width}_num={Number of cycles}_ampl={Pulse amplitude:.0f}"


if __name__ == "__main__":
    setup_file_logging("logs")
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
