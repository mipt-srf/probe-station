import logging

from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter, Parameter

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.common import BaseProcedure, BaseWindow, run_app
from probe_station.measurements.keithley.cycling import cycle
from probe_station.measurements.keithley.device import connect_instrument, get_smu, set_smu
from probe_station.measurements.keithley.launcher import ADDRESS
from probe_station.measurements.keithley.PUND_waveform import create_waveform

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class PundProcedure(BaseProcedure):
    terminal = Parameter("Terminal", default="rear")
    vf = FloatParameter("First voltage", units="V", default=-3)
    vs = FloatParameter("Second voltage", units="V", default=3)
    rise = IntegerParameter("Rise steps", default=50)
    hold = IntegerParameter("Hold steps", default=5)
    space = IntegerParameter("Space steps", default=5)
    n_cycles = IntegerParameter("PUND cycles", default=1)
    average_cycles = BooleanParameter("Average cycles", default=False)
    int_time = FloatParameter("Integration time", units="s", default=0)
    # compliance = FloatParameter("Compliance current", units="A", default=1e-4)
    autorange = BooleanParameter("Autorange", default=False)
    current_range = FloatParameter(
        "Current range", units="A", default=1e-4, group_by="autorange", group_condition=False
    )
    # counts = IntegerParameter("Averaging", default=1)
    do_cycle = BooleanParameter("Pre-cycle", default=False)
    n_precycles = IntegerParameter("Pre-cycle count", default=50, group_by="do_cycle")

    DATA_COLUMNS = ["Time", "Source", "Reading"]

    def startup(self):
        super().startup()
        self.smu = get_smu()

    def execute(self):
        log.info("Starting %s", self.__class__.__name__)
        self.smu.set_terminal(self.terminal)
        self.smu.raise_error()

        if self.do_cycle:
            log.info("Pre-cycling %d times", self.n_precycles)
            cycle(self.smu, self.n_precycles, self.vf, self.vs)
            if self.should_stop():
                return
            self.smu.raise_error()

        self.smu.setup_sense_subsystem(
            # compl=self.compliance,
            compl=self.current_range,
            range=self.current_range,
            autorange=self.autorange,
            int_time=self.int_time,
            # counts=self.counts,
        )
        self.smu.setup_source_subsystem()
        self.smu.raise_error()

        waveform = self._create_waveform()
        log.info("Initiating waveform with %d points", len(waveform))
        self.smu.voltage_list_sweep(waveform, self.n_cycles)
        self.smu.initiate()
        self.smu.wait(self.should_stop)

        if self.should_stop():
            log.info("Aborted during sweep")
            return

        self.smu.raise_error()
        data = self.smu.get_traces()

        time, source, reading = data["time"], data["source"], data["reading"]
        if self.average_cycles and self.n_cycles > 1:
            n = len(time) // self.n_cycles
            reading = [sum(reading[i + n * c] for c in range(self.n_cycles)) / self.n_cycles for i in range(n)]
            time, source = time[:n], source[:n]

        total = len(time)
        for i, (t, src, r) in enumerate(zip(time, source, reading)):
            self.emit("results", {"Time": t, "Source": src, "Reading": r})
            self.emit("progress", (i + 1) / total * 100)
            if self.should_stop():
                break

    def _create_waveform(self):
        params = {
            "Vf": self.vf,
            "Vs": self.vs,
            "rise": self.rise,
            "hold": self.hold,
            "space": self.space,
            "n_cycles": self.n_cycles,
        }
        return create_waveform(params, by_rate=False)


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            PlotWidget("Results Graph", PundProcedure.DATA_COLUMNS, x_axis="Source", y_axis="Reading"),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=PundProcedure,
            widget_list=widget_list,
            logger=log,
        )
        from qtpy.QtWidgets import QLabel

        self._pulse_label = QLabel()
        self.inputs.layout().addWidget(self._pulse_label)
        self.inputs.rise.valueChanged.connect(self._update_pulse_duration)
        self.inputs.hold.valueChanged.connect(self._update_pulse_duration)
        self.inputs.int_time.valueChanged.connect(self._update_pulse_duration)
        self._update_pulse_duration()

    def _update_pulse_duration(self):
        rise = self.inputs.rise.value()
        hold = self.inputs.hold.value()
        int_time = self.inputs.int_time.value()
        effective_nplc = max(0.01, int_time * 60)
        duration = round((2 * rise + hold) * effective_nplc / 60 * 1e3 * 3, 3)  # factor of 3 due to ???
        self._pulse_label.setText(f"Pulse duration: {duration} ms")


if __name__ == "__main__":
    setup_file_logging("logs")
    set_smu(connect_instrument(ADDRESS))
    run_app(MainWindow)
