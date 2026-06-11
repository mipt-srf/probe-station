import logging

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    ListParameter,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.b1500 import WGFMUMeasureCurrentRange
from probe_station.measurements.b1500_helpers import max_compliance
from probe_station.measurements.pymeasure_base import BaseWindow, run_app
from probe_station.measurements.smu._widgets import IvPlotWidget
from probe_station.measurements.wgfmu._base import WgfmuProcedure
from probe_station.measurements.wgfmu._waveforms import (
    SweepMode,
    get_constant_sequence,
    get_sequence,
    run_waveforms,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class WgfmuFetIdsVgProcedure(WgfmuProcedure):
    """FET transfer (Ids-Vg) sweep on the WGFMU.

    The gate channel is driven with a triangular voltage sweep while the drain
    channel is held at a constant Vds. Both channels measure current at aligned
    time points, so the drain current sampled against the gate voltage gives the
    transfer curve. Mirrors the SMU ``Ids (Vg)`` procedure but uses the fast
    WGFMU waveform path like the WGFMU IV sweep.

    The two idle terminals -- source and substrate (base) -- are held at 0 V via
    SMU channels for the duration of the sweep, matching the grounding done by
    the SMU ``Ids (Vg)`` procedure (textbook setup: source grounded, Vds on the
    drain). These are plain SMU probes, so they need no RSU routing change.
    """

    # Parameters are declared in GUI order (see WgfmuProcedure): sweep
    # timing, channels, voltages, current range, then the advanced-config
    # section. The sweep parameters are shared with WgfmuBaseProcedure but cannot
    # be inherited without scrambling that order, so they are declared here too.
    mode = ListParameter("Mode", default=SweepMode.DEFAULT.name, choices=[e.name for e in SweepMode])
    pulse_time = FloatParameter("Pulse time", units="s", default=1e-3)

    gate = IntegerParameter("Gate channel (WGFMU)", default=2)
    drain = IntegerParameter("Drain channel (WGFMU)", default=1)
    source = IntegerParameter("Source channel (SMU, grounded)", default=1)
    base = IntegerParameter("Base channel (SMU, grounded)", default=2)

    voltage_ds = FloatParameter("Drain-source voltage", units="V", default=0.25)
    voltage_gate_first = FloatParameter("Gate voltage (first)", units="V", default=-5.0)
    voltage_gate_second = FloatParameter("Gate voltage (second)", units="V", default=5.0)

    current_range = ListParameter(
        "Current range",
        default=WGFMUMeasureCurrentRange.RANGE_10_MA.name,
        choices=[e.name for e in WGFMUMeasureCurrentRange],
    )

    advanced_config = BooleanParameter("Advanced config", default=False)
    steps = IntegerParameter("Steps per pulse", default=100, group_by="advanced_config")
    rise_to_hold_ratio = FloatParameter("Rise to hold time ratio", default=1, group_by="advanced_config")

    plot_points = IntegerParameter("Points to plot", default=200, group_by="advanced_config")

    DATA_COLUMNS = ["Gate Voltage", "Drain-Source Current", "Gate Current", "Time"]

    def execute(self):
        # Hold the idle terminals (source, substrate) at 0 V via SMUs for the
        # whole sweep, mirroring the SMU Ids(Vg) grounding.
        for channel in (self.source, self.base):
            smu = self.b1500.smus[channel]
            smu.enable()
            smu.force("voltage", 0, 0, max_compliance(smu, 0))

        seq_gate = get_sequence(
            sequence_type=self.mode.lower(),
            pulse_time=self.pulse_time,
            first_voltage=self.voltage_gate_first,
            second_voltage=self.voltage_gate_second,
            steps=self.steps,
            rise_to_hold_ratio=self.rise_to_hold_ratio,
            trailing_pulse=True,
        )
        # Built after seq_gate so the constant drain bias spans the full gate
        # duration, including the trailing pulse, keeping both channels aligned.
        seq_drain = get_constant_sequence(self.voltage_ds, seq_gate.total_duration)

        gate_data, drain_data = run_waveforms(
            b1500=self.b1500,
            top_seq=seq_gate,
            top_ch=self.gate,
            bottom_seq=seq_drain,
            bottom_ch=self.drain,
            repetitions=1,
            current_range=WGFMUMeasureCurrentRange[self.current_range],
            measure=True,
            plot_points=self.plot_points,
        )

        times, gate_voltages, gate_currents = gate_data
        _, _, drain_currents = drain_data

        self.emit(
            "batch results",
            {
                "Gate Voltage": gate_voltages,
                "Drain-Source Current": drain_currents,
                "Gate Current": gate_currents,
                "Time": times,
            },
        )


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            IvPlotWidget("Results Graph", WgfmuFetIdsVgProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=WgfmuFetIdsVgProcedure,
            widget_list=widget_list,
            logger=log,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
