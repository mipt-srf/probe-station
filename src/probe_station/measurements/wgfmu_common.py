"""Shared WGFMU helpers for voltage-sweep and cycling procedures."""

import logging
from enum import Enum

import numpy as np
import scipy
from keysight_b1530a._bindings.config import WGFMUChannel
from waveform_generator import PulseSequence, TrapezoidalPulse, TriangularSweep

from probe_station.measurements.b1500 import (
    B1500,
    WGFMUMeasureCurrentRange,
    WGFMUMeasureEvent,
    WGFMUMeasureMode,
    WGFMUOperationMode,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SweepMode(Enum):
    DEFAULT = "default"
    PUND = "pund"


def calculate_polarization(times, currents, pad_size_um):
    charge = scipy.integrate.simpson(y=np.abs(currents), x=times)
    area = (pad_size_um * 1e-4) ** 2
    return charge / area * 1e6


def get_sequence(
    sequence_type="pund",
    pulse_time=2e-4,
    steps=200,
    max_voltage=4,
    min_voltage=-4,
    rise_to_hold_ratio=0.01,
    *,
    trailing_pulse: bool = False,
):
    time_step = pulse_time / steps / (1 + rise_to_hold_ratio)
    edge_time = time_step * rise_to_hold_ratio

    positive = TriangularSweep(end_voltage=max_voltage, time_step=time_step, steps=steps, edge_time=edge_time)
    negative = TriangularSweep(end_voltage=min_voltage, time_step=time_step, steps=steps, edge_time=edge_time)

    if sequence_type == "pund":
        pulses = [positive] * 2 + [negative] * 2
        if trailing_pulse:
            # delay pulse so the last measurement points are not clipped
            pulses.append(
                TrapezoidalPulse(amplitude=0.0, pulse_width=edge_time, rise_time=10 * edge_time, fall_time=edge_time)
            )
        return PulseSequence(pulses)
    return PulseSequence([positive, negative])


def set_waveform(
    b1500: B1500,
    sequence,
    *,
    repetitions=1,
    channel=WGFMUChannel.CH1,
    measure=True,
    measure_points=1600,
    pattern_name="sequence",
    interval_scale: float = 1.0,
):
    pattern_name += f"_{channel.name.lower()}"
    b1500.create_wgfmu_pattern(pattern_name, sequence.pulses[0].dc_bias)
    times, voltages = sequence.to_vectors()
    seq_time = sequence.total_duration
    log.info(f"Waveform for {pattern_name}: {len(voltages)} samples, {seq_time:.6g} s, {len(sequence.pulses)} pulses")
    b1500.add_vectors_to_wgfmu_pattern(pattern_name, times, voltages)
    if measure:
        b1500.set_wgfmu_measure_event(
            pattern_name=pattern_name,
            event_name="event",
            points=measure_points,
            interval=seq_time / measure_points * interval_scale,
            average=seq_time / measure_points,
            mode=WGFMUMeasureEvent.AVERAGED,
        )
    wgfmu = b1500.wgfmus[channel.value - 200]
    wgfmu.add_sequence(pattern_name, repetitions=repetitions)


def run(
    b1500: B1500,
    *,
    channels=None,
    mode=WGFMUOperationMode.FASTIV,
    measure_range=WGFMUMeasureCurrentRange.RANGE_1_UA,
    configure_measure_mode: bool = True,
):
    if channels is None:
        channels = [WGFMUChannel.CH2]
    for channel in channels:
        wgfmu = b1500.wgfmus[channel.value - 200]
        wgfmu.set_operation_mode(mode)
        if configure_measure_mode:
            wgfmu.set_measure_mode(WGFMUMeasureMode.CURRENT)
            wgfmu.set_measure_current_range(measure_range)
        wgfmu.enable()
    b1500.run_wgfmu_measurement()


def get_data(
    b1500: B1500,
    *,
    channel=WGFMUChannel.CH2,
    repetitions=1,
    points: int | None = None,
):
    wgfmu = b1500.wgfmus[channel.value - 200]
    times, currents = wgfmu.get_measurement_data()
    voltages = wgfmu.get_voltage_data()

    if points is None:
        log.debug(f"Raw data length: {len(voltages)}")
        return times, voltages, currents

    times = np.split(np.array(times), repetitions)[-1]
    currents = np.split(np.array(currents), repetitions)[-1]
    voltages = np.split(np.array(voltages), repetitions)[-1]
    log.debug(f"Raw voltage array length (last rep): {len(voltages)}")

    times = np.mean(times.reshape(-1, len(voltages) // points), axis=1)
    currents = np.mean(currents.reshape(-1, len(voltages) // points), axis=1)
    voltages = np.mean(voltages.reshape(-1, len(voltages) // points), axis=1)
    log.debug(f"Decimated voltage array length: {len(voltages)}")

    return times, voltages, currents
