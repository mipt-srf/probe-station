"""Pulse-amplitude sweep: apply a single unipolar pulse, then run an IV sweep.

For each amplitude in a linear range, a single unipolar triangular pulse
(0 -> +amplitude -> 0) is applied to the top electrode and followed by a WGFMU
IV sweep (0 -> +V -> -V -> 0). Each IV sweep is saved as its own CSV labelled
with the pulse amplitude, mirroring the raw-run layout of :mod:`wgfmu_endurance`.
"""

import logging
import shutil
from pathlib import Path

import numpy as np

from probe_station.experiments.common import run
from probe_station.logging_setup import add_file_log_dir, setup_file_logging
from probe_station.measurements.b1500 import WGFMUMeasureCurrentRange
from probe_station.measurements.wgfmu._waveforms import SweepMode, WaveformShape
from probe_station.measurements.wgfmu.cycling import WgfmuCyclingProcedure
from probe_station.measurements.wgfmu.iv_sweep import WgfmuIvSweepProcedure

folder = "pulse_iv"

logger = logging.getLogger(__name__)


def pulse_proc(amplitude, pulse_time=1e-5, channel=2, steps=50):
    """Single unipolar triangular pulse (0 -> +amplitude -> 0) on the top electrode.

    Reuses the cycling procedure with one repetition and the UNIPOLAR sequence
    type so only the positive half is played; no current is measured.
    """
    return WgfmuCyclingProcedure(
        mode=SweepMode.UNIPOLAR.name,
        repetitions=1,
        pulse_time=pulse_time,
        voltage_top_first=amplitude,
        top=channel,
        steps=steps,
        waveform_shape=WaveformShape.TRIANGLE.name,
    )


def iv_proc(
    voltage=5.0,
    pulse_time=1e-5,
    top=2,
    bottom=1,
    current_range=WGFMUMeasureCurrentRange.RANGE_1_MA.name,
):
    """WGFMU IV sweep 0 -> +voltage -> -voltage -> 0 (DEFAULT triangular sweep)."""
    return WgfmuIvSweepProcedure(
        mode=SweepMode.DEFAULT.name,
        voltage_top_first=voltage,
        voltage_top_second=-voltage,
        pulse_time=pulse_time,
        top=top,
        enable_bottom=True,
        voltage_bottom_first=0.0,
        voltage_bottom_second=0.0,
        bottom=bottom,
        current_range=current_range,
        bottom_current_range=WGFMUMeasureCurrentRange.RANGE_10_UA.name,
        steps=50,
        rise_to_hold_ratio=1,
        waveform_shape=WaveformShape.TRIANGLE.name,
        plot_points=200,
    )


def pulse_iv(
    amplitude_start=1.0,
    amplitude_stop=5.0,
    amplitude_step=0.5,
    pulse_time=1e-5,
    iv_voltage=5.0,
    iv_time=1e-5,
    channel=2,
):
    """Apply a single unipolar pulse then run an IV sweep, for each pulse amplitude.

    Iterates the pulse amplitude over the inclusive linear range
    ``[amplitude_start, amplitude_stop]`` with ``amplitude_step`` spacing. Each
    IV sweep is written to its own CSV in ``folder`` labelled with the amplitude.
    """
    # add half a step so a *stop* that lands on the grid is included despite
    # floating-point rounding
    for amplitude in np.arange(amplitude_start, amplitude_stop + amplitude_step / 2, amplitude_step):
        amplitude = round(float(amplitude), 3)
        logger.info(f"=================== Pulse amplitude: {amplitude} V ===================")

        run(
            pulse_proc(amplitude, pulse_time=pulse_time, channel=channel),
            folder=folder,
            timeout=60 * 5,
            startup_delay=5,
            suffix=f"_pulse_{amplitude:g}V",
        )
        run(
            iv_proc(voltage=iv_voltage, pulse_time=iv_time, top=channel),
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
