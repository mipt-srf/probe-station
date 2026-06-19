"""Pulse-amplitude sweep: apply a single unipolar gate pulse, then run an Ids(Vg) sweep.

For each amplitude in a linear range, a single unipolar triangular pulse
(0 -> +amplitude -> 0) is applied to the gate and followed by a WGFMU FET
transfer sweep (gate 0 -> +V -> -V -> 0). Both steps use
:class:`WgfmuFetIdsVgProcedure` so the drain stays biased at Vds and the
substrate grounded throughout. Each sweep is saved as its own CSV labelled with
the pulse amplitude, mirroring the raw-run layout of :mod:`wgfmu_endurance`.
"""

import logging
import shutil
from pathlib import Path

import numpy as np

from probe_station.experiments.common import run
from probe_station.logging_setup import add_file_log_dir, setup_file_logging
from probe_station.measurements.b1500 import WGFMUMeasureCurrentRange
from probe_station.measurements.wgfmu._waveforms import SweepMode, WaveformShape
from probe_station.measurements.wgfmu.fet_ids_vg import WgfmuFetIdsVgProcedure

folder = "chosen_pulse_iv"

logger = logging.getLogger(__name__)


def pulse_proc(amplitude, pulse_time=1e-5, gate=2, steps=50, voltage_ds=0.0):
    """Single unipolar triangular gate pulse (0 -> +amplitude -> 0).

    Reuses the FET Ids(Vg) procedure with the UNIPOLAR sequence type so only a
    single conditioning pulse is played on the gate. The drain bias defaults to
    0 V so the pulse only conditions the gate stack.
    """
    return WgfmuFetIdsVgProcedure(
        mode=SweepMode.UNIPOLAR.name,
        pulse_time=pulse_time,
        gate_channel=gate,
        voltage_ds=voltage_ds,
        voltage_gate_first=amplitude,
        steps=steps,
        waveform_shape=WaveformShape.TRIANGLE.name,
    )


def iv_proc(
    voltage=5.0,
    pulse_time=1e-5,
    gate=2,
    voltage_ds=-0.25,
    current_range=WGFMUMeasureCurrentRange.RANGE_1_MA.name,
    source_current_range=WGFMUMeasureCurrentRange.RANGE_10_MA.name,
):
    """FET transfer sweep with the gate swept 0 -> +voltage -> -voltage -> 0."""
    return WgfmuFetIdsVgProcedure(
        mode=SweepMode.DEFAULT.name,
        pulse_time=pulse_time,
        gate_channel=gate,
        voltage_ds=voltage_ds,
        voltage_gate_first=voltage,
        voltage_gate_second=-voltage,
        current_range=current_range,
        source_current_range=source_current_range,
        steps=50,
        rise_to_hold_ratio=1,
        waveform_shape=WaveformShape.TRIANGLE.name,
        plot_points=200,
    )


def pulse_iv(
    amplitude_start=0.0,
    amplitude_stop=10.0,
    amplitude_step=0.2,
    pulse_time=1e-5,
    iv_voltage=5.0,
    iv_time=1e-5,
    channel=2,
):
    """Apply a single unipolar gate pulse then run an Ids(Vg) sweep, per amplitude.

    Iterates the pulse amplitude over the inclusive linear range
    ``[amplitude_start, amplitude_stop]`` with ``amplitude_step`` spacing. Each
    transfer sweep is written to its own CSV in ``folder`` labelled with the
    amplitude.
    """
    # add half a step so a *stop* that lands on the grid is included despite
    # floating-point rounding
    for amplitude in np.arange(amplitude_start, amplitude_stop + amplitude_step / 2, amplitude_step):
        amplitude = round(float(amplitude), 3)
        logger.info(f"=================== Pulse amplitude: {amplitude} V ===================")

        run(
            pulse_proc(amplitude, pulse_time=pulse_time, gate=channel),
            folder=folder,
            timeout=60 * 5,
            startup_delay=5,
            suffix=f"_pulse_{amplitude:g}V",
        )
        run(
            iv_proc(voltage=iv_voltage, pulse_time=iv_time, gate=channel),
            folder=folder,
            timeout=60 * 10,
            suffix=f"_iv_{amplitude:g}V",
        )

        amplitude = -amplitude
        run(
            pulse_proc(amplitude, pulse_time=pulse_time, gate=channel),
            folder=folder,
            timeout=60 * 5,
            startup_delay=5,
            suffix=f"_pulse_{amplitude:g}V",
        )
        run(
            iv_proc(voltage=iv_voltage, pulse_time=iv_time, gate=channel),
            folder=folder,
            timeout=60 * 10,
            suffix=f"_iv_{amplitude:g}V",
        )


if __name__ == "__main__":
    shutil.rmtree(Path(folder), ignore_errors=True)
    Path(folder).mkdir(exist_ok=True)
    setup_file_logging()
    add_file_log_dir(Path(folder) / "logs")

    pulse_iv()
