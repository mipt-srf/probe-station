import logging
from typing import cast

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
    WaveformShape,
    get_constant_sequence,
    get_sequence,
    on_grid_duration,
    run_waveforms,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class WgfmuFetIdsVgProcedure(WgfmuProcedure):
    """FET transfer (Ids-Vg) sweep on the WGFMU.

    The gate WGFMU channel is driven with a triangular voltage sweep while the
    second WGFMU channel grounds the source at 0 V; both measure current at
    aligned time points, so the source current sampled against the gate voltage
    gives the transfer curve (Is = Id + Ig). The drain only needs a constant
    Vds, so it is biased by its SMU, freeing the second WGFMU channel for the
    source. The substrate (base) is grounded via a plain SMU probe.
    """

    # Parameters are declared in GUI order (see WgfmuProcedure): sweep
    # timing, channels, voltages, current range, then the advanced-config
    # section. The sweep parameters are shared with WgfmuBaseProcedure but cannot
    # be inherited without scrambling that order, so they are declared here too.
    mode: str = cast("str", ListParameter("Mode", default=SweepMode.DEFAULT.name, choices=[e.name for e in SweepMode]))
    pulse_time: float = cast("float", FloatParameter("Pulse time", units="s", default=1e-3))

    gate_channel: int = cast("int", IntegerParameter("Gate channel (WGFMU)", default=2))
    source_channel: int = cast("int", IntegerParameter("Source channel (WGFMU, grounded)", default=1))
    drain_channel: int = cast("int", IntegerParameter("Drain channel (SMU, biased)", default=1))
    base_channel: int = cast("int", IntegerParameter("Base channel (SMU, grounded)", default=2))

    drain_voltage: float = cast("float", FloatParameter("Drain voltage", units="V", default=0.25))
    gate_voltage_first: float = cast("float", FloatParameter("Gate voltage (first)", units="V", default=-5.0))
    gate_voltage_second: float = cast("float", FloatParameter("Gate voltage (second)", units="V", default=5.0))

    current_range: str = cast(
        "str",
        ListParameter(
            "Current range",
            default=WGFMUMeasureCurrentRange.RANGE_10_MA.name,
            choices=[e.name for e in WGFMUMeasureCurrentRange],
        ),
    )
    source_current_range: str = cast(
        "str",
        ListParameter(
            "Source current range",
            default=WGFMUMeasureCurrentRange.RANGE_10_MA.name,
            choices=[e.name for e in WGFMUMeasureCurrentRange],
        ),
    )

    advanced_config: bool = cast("bool", BooleanParameter("Advanced config", default=False))
    steps: int = cast("int", IntegerParameter("Steps per pulse", default=50, group_by="advanced_config"))
    waveform_shape: str = cast(
        "str",
        ListParameter(
            "Waveform shape",
            default=WaveformShape.STAIRCASE.name,
            choices=[e.name for e in WaveformShape],
            group_by="advanced_config",
        ),
    )
    rise_to_hold_ratio: float = cast(
        "float", FloatParameter("Rise to hold time ratio", default=1, group_by="advanced_config")
    )

    plot_points: int = cast("int", IntegerParameter("Points to plot", default=200, group_by="advanced_config"))

    DATA_COLUMNS = ["Gate Voltage", "Source Current", "Gate Current", "Time"]

    def execute(self):
        # Bias the drain at a constant Vds via its SMU and ground the substrate
        # (base); the source is grounded and measured by the second WGFMU
        # channel below.
        smu_drain = self.b1500.smus[self.drain_channel]
        smu_drain.enable()
        smu_drain.force("voltage", 0, self.drain_voltage, max_compliance(smu_drain, abs(self.drain_voltage)))

        smu_base = self.b1500.smus[self.base_channel]
        smu_base.enable()
        smu_base.force("voltage", 0, 0, max_compliance(smu_base, 0))

        seq_gate = get_sequence(
            sequence_type=self.mode.lower(),
            pulse_time=self.pulse_time,
            first_voltage=self.gate_voltage_first,
            second_voltage=self.gate_voltage_second,
            steps=self.steps,
            rise_to_hold_ratio=self.rise_to_hold_ratio,
            shape=self.waveform_shape.lower(),
            trailing_pulse=True,
        )
        # Built after seq_gate so the source ground spans the full gate
        # duration, including the trailing pulse, keeping both channels
        # aligned. The on-grid duration is what the hardware actually plays;
        # the nominal total_duration would skew the channels apart at short
        # pulse times where per-segment 10 ns rounding accumulates.
        seq_source = get_constant_sequence(0.0, on_grid_duration(seq_gate))

        try:
            gate_data, source_data = run_waveforms(
                b1500=self.b1500,
                top_seq=seq_gate,
                top_ch=self.gate_channel,
                bottom_seq=seq_source,
                bottom_ch=self.source_channel,
                repetitions=1,
                current_range=WGFMUMeasureCurrentRange[self.current_range],
                bottom_current_range=WGFMUMeasureCurrentRange[self.source_current_range],
                measure=True,
                plot_points=self.plot_points,
            )
        finally:
            # Always return the drain SMU to 0 V so a failed sweep does not
            # leave the FET biased, which would rewrite its state.
            smu_drain.force("voltage", 0, 0)

        times, gate_voltages, gate_currents = gate_data
        _, _, source_currents = source_data

        self.emit(
            "batch results",
            {
                "Gate Voltage": gate_voltages,
                "Source Current": source_currents,
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
            logger=logger,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
