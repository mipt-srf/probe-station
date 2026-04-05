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
    hold = IntegerParameter("Hold steps", default=10)
    space = IntegerParameter("Space steps", default=75)
    n_cycles = IntegerParameter("PUND cycles", default=1)
    int_time = FloatParameter("Integration time", units="s", default=0)
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

        self.smu.setup_sense_subsystem(compl=1e-4, range=1e-4, int_time=self.int_time, counts=1)
        self.smu.setup_source_subsystem()
        self.smu.raise_error()

        params = {
            "Vf": self.vf,
            "Vs": self.vs,
            "rise": self.rise,
            "hold": self.hold,
            "space": self.space,
            "n_cycles": self.n_cycles,
        }
        waveform = create_waveform(params, by_rate=False)
        log.info("Initiating PUND waveform with %d points", len(waveform))
        self.smu.voltage_list_sweep(waveform, self.n_cycles)
        self.smu.initiate()
        self.smu.wait()

        self.smu.raise_error()
        data = self.smu.get_traces()

        total = len(data["time"])
        for i, (t, src, reading) in enumerate(zip(data["time"], data["source"], data["reading"])):
            self.emit("results", {"Time": t, "Source": src, "Reading": reading})
            self.emit("progress", (i + 1) / total * 100)
            if self.should_stop():
                break


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            PlotWidget("Results Graph", PundProcedure.DATA_COLUMNS, x_axis="Time", y_axis="Reading"),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=PundProcedure,
            widget_list=widget_list,
            logger=log,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    set_smu(connect_instrument(ADDRESS))
    run_app(MainWindow)
