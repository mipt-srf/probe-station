"""Shared base procedure for WGFMU-based measurements."""

from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    ListParameter,
)

from probe_station.measurements.pymeasure_base import BaseProcedure
from probe_station.measurements.session import Session
from probe_station.measurements.wgfmu._waveforms import SweepMode, WaveformShape


class WgfmuProcedure(BaseProcedure):
    """WGFMU instrument startup shared by all WGFMU-based procedures.

    Holds only the instrument setup common to every WGFMU procedure, regardless
    of how the device under test is wired. Subclass this directly when the
    top/bottom electrode model in :class:`WgfmuBaseProcedure` does not fit (e.g.
    a FET with separate gate and drain channels).

    Parameters are intentionally *not* declared here. ``BaseWindow`` lays the GUI
    out by walking the MRO parent-first, so any parameter on a shared parent
    sorts before a subclass's own parameters and scrambles the on-screen order.
    Keeping this base parameter-free lets each concrete procedure declare its
    inputs in a single flat body, where declaration order is the GUI order.
    """

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire(timeout=60000, reset=False)
        self.b1500.clear_wgfmu()
        self.b1500.initialize_wgfmu()


class WgfmuBaseProcedure(WgfmuProcedure):
    """Shared parameters for two-electrode (top/bottom) WGFMU sweeps.

    Parameters are declared in GUI order (see :class:`WgfmuProcedure`).
    """

    mode = ListParameter("Mode", default=SweepMode.DEFAULT.name, choices=[e.name for e in SweepMode])
    pulse_time = FloatParameter("Pulse time", units="s", default=1e-5)

    top_voltage_first = FloatParameter("Top electrode voltage (first)", units="V", default=5.0)
    top_voltage_second = FloatParameter("Top electrode voltage (second)", units="V", default=-5.0)

    top = IntegerParameter("Top channel", default=2)

    enable_bottom = BooleanParameter("Enable bottom bias and measurement", default=False)

    bottom_voltage_first = FloatParameter(
        "Bottom electrode voltage (first)", units="V", default=-5.0, group_by="enable_bottom"
    )
    bottom_voltage_second = FloatParameter(
        "Bottom electrode voltage (second)", units="V", default=5.0, group_by="enable_bottom"
    )
    bottom = IntegerParameter("Bottom channel", default=1, group_by="enable_bottom")

    advanced_config = BooleanParameter("Advanced config", default=False)

    steps = IntegerParameter("Steps per pulse", default=100, group_by="advanced_config")
    waveform_shape = ListParameter(
        "Waveform shape",
        default=WaveformShape.STAIRCASE.name,
        choices=[e.name for e in WaveformShape],
        group_by="advanced_config",
    )
    rise_to_hold_ratio = FloatParameter("Rise to hold time ratio", default=1, group_by="advanced_config")
