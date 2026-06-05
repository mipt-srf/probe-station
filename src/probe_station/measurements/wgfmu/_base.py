"""Shared base procedure for WGFMU-based measurements."""

from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    ListParameter,
)

from probe_station.measurements.b1500 import WGFMUMeasureCurrentRange
from probe_station.measurements.pymeasure_base import BaseProcedure
from probe_station.measurements.session import Session
from probe_station.measurements.wgfmu._waveforms import SweepMode


class WgfmuSweepProcedure(BaseProcedure):
    """Generic WGFMU startup and sweep parameters (no electrode topology).

    Holds the parameters and instrument setup common to every WGFMU-based
    procedure, regardless of how the device under test is wired. Subclass this
    directly when the top/bottom electrode model in :class:`WgfmuBaseProcedure`
    does not fit (e.g. a FET with separate gate and drain channels).
    """

    mode = ListParameter("Mode", default=SweepMode.DEFAULT.name, choices=[e.name for e in SweepMode])
    pulse_time = FloatParameter("Pulse time", units="s", default=1e-5)

    current_range = ListParameter(
        "Current range",
        default=WGFMUMeasureCurrentRange.RANGE_100_UA.name,
        choices=[e.name for e in WGFMUMeasureCurrentRange],
    )

    advanced_config = BooleanParameter("Advanced config", default=False)

    steps = IntegerParameter("Steps per pulse", default=100, group_by="advanced_config")
    rise_to_hold_ratio = FloatParameter("Rise to hold time ratio", default=1, group_by="advanced_config")

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire(timeout=60000, reset=False)
        self.b1500.clear_wgfmu()
        self.b1500.initialize_wgfmu()


class WgfmuBaseProcedure(WgfmuSweepProcedure):
    """Shared parameters for two-electrode (top/bottom) WGFMU sweeps."""

    voltage_top_first = FloatParameter("Top electrode voltage (first)", units="V", default=5.0)
    voltage_top_second = FloatParameter("Top electrode voltage (second)", units="V", default=-5.0)

    top = IntegerParameter("Top channel", default=2)

    enable_bottom = BooleanParameter("Enable bottom bias and measurement", default=False)

    voltage_bottom_first = FloatParameter(
        "Bottom electrode voltage (first)", units="V", default=-5.0, group_by="enable_bottom"
    )
    voltage_bottom_second = FloatParameter(
        "Bottom electrode voltage (second)", units="V", default=5.0, group_by="enable_bottom"
    )
    bottom = IntegerParameter("Bottom channel", default=1, group_by="enable_bottom")
