"""Shared WGFMU helpers for voltage-sweep and cycling procedures."""

import logging
from enum import Enum

import numpy as np
import scipy
from keysight_b1530a._bindings.errors import get_error_summary
from keysight_b1530a.errors import WGFMUError
from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    ListParameter,
)
from waveform_generator import PulseSequence, TrapezoidalPulse, TriangularSweep

from probe_station.measurements.b1500 import (
    B1500,
    WGFMUMeasureCurrentRange,
    WGFMUMeasureEvent,
    WGFMUMeasureMode,
    WGFMUOperationMode,
)
from probe_station.measurements.common import BaseProcedure, connect_instrument

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
    channel=1,
    measure=True,
    measure_points=1600,
    pattern_name="sequence",
    interval_scale: float = 1.0,
):
    pattern_name += f"_wgfmu{channel}"
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
    wgfmu = b1500.wgfmus[channel]
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
        channels = [2]
    for channel in channels:
        wgfmu = b1500.wgfmus[channel]
        wgfmu.set_operation_mode(mode)
        if configure_measure_mode:
            wgfmu.set_measure_mode(WGFMUMeasureMode.CURRENT)
            wgfmu.set_measure_current_range(measure_range)
        wgfmu.enable()
    b1500.run_wgfmu_measurement()


def get_data(
    b1500: B1500,
    *,
    channel=2,
    repetitions=1,
    points: int | None = None,
):
    wgfmu = b1500.wgfmus[channel]
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


def run_waveforms(
    b1500: B1500,
    *,
    top_seq,
    top_ch: int,
    bottom_seq=None,
    bottom_ch: int | None = None,
    repetitions: int,
    current_range: WGFMUMeasureCurrentRange,
    measure: bool,
    plot_points: int | None = None,
    interval_scale: float = 1.0,
):
    """Set waveforms on top (and optional bottom), run, optionally fetch data.

    Returns ``None`` when ``measure`` is False; otherwise returns
    ``(top_data, bottom_data)`` where each entry is ``(times, voltages, currents)``
    (and ``bottom_data`` is ``None`` when no bottom channel is provided).
    """
    set_waveform(
        b1500=b1500,
        sequence=top_seq,
        repetitions=repetitions,
        channel=top_ch,
        measure=measure,
        measure_points=plot_points or 0,
        interval_scale=interval_scale,
    )
    if bottom_seq is not None:
        set_waveform(
            b1500=b1500,
            sequence=bottom_seq,
            repetitions=repetitions,
            channel=bottom_ch,
            measure=measure,
            measure_points=plot_points or 0,
            interval_scale=interval_scale,
        )

    channels = [top_ch] if bottom_ch is None else [top_ch, bottom_ch]
    try:
        run(
            b1500=b1500,
            channels=channels,
            measure_range=current_range,
            configure_measure_mode=measure,
        )
    except WGFMUError:
        log.error(f"{get_error_summary()}")
        b1500.clear_wgfmu()
        b1500.close_wgfmu_session()
        raise

    if not measure:
        return None

    top_data = get_data(b1500=b1500, channel=top_ch, repetitions=repetitions, points=plot_points)
    bottom_data = None
    if bottom_ch is not None:
        bottom_data = get_data(b1500=b1500, channel=bottom_ch, repetitions=repetitions, points=plot_points)
    return top_data, bottom_data


def _stitch(chunk_a, chunk_b):
    t1, v1, c1 = chunk_a
    t2, v2, c2 = chunk_b
    return (
        np.concatenate([t1, t2]),
        np.concatenate([v1, v2]),
        np.concatenate([c1, c2]),
    )


def run_waveforms_split(
    b1500: B1500,
    *,
    top_seq,
    top_ch: int,
    bottom_seq,
    bottom_ch: int,
    current_range: WGFMUMeasureCurrentRange,
    plot_points: int,
    interval_scale: float = 1.0,
):
    """Split a PUND sequence into positive/negative halves and run each separately.

    Used when the top/bottom differential exceeds the 10 V per-channel limit:
    biasing one electrode negative while driving the other positive doubles
    the addressable range, but only one polarity can be applied at a time.
    Requires a bottom electrode and always measures; data is stitched across
    the two halves.
    """
    n = len(top_seq.pulses)
    if n != len(bottom_seq.pulses):
        raise ValueError("top and bottom sequences must have the same pulse count")
    if n < 2:
        raise ValueError(f"split path requires at least 2 pulses, got {n}")
    half = n // 2
    half_points = plot_points // 2

    halves = [
        ("pu", PulseSequence(top_seq.pulses[:half]), PulseSequence(bottom_seq.pulses[:half])),
        ("nd", PulseSequence(top_seq.pulses[half:]), PulseSequence(bottom_seq.pulses[half:])),
    ]

    top_chunks = []
    bottom_chunks = []
    for name, half_top, half_bot in halves:
        set_waveform(
            b1500=b1500,
            sequence=half_top,
            repetitions=1,
            channel=top_ch,
            measure=True,
            measure_points=half_points,
            pattern_name=f"top_{name}",
            interval_scale=interval_scale,
        )
        set_waveform(
            b1500=b1500,
            sequence=half_bot,
            repetitions=1,
            channel=bottom_ch,
            measure=True,
            measure_points=half_points,
            pattern_name=f"bottom_{name}",
            interval_scale=interval_scale,
        )
        try:
            run(
                b1500=b1500,
                channels=[top_ch, bottom_ch],
                measure_range=current_range,
                configure_measure_mode=True,
            )
        except WGFMUError:
            log.error(f"{get_error_summary()}")
            b1500.clear_wgfmu()
            b1500.close_wgfmu_session()
            raise

        top_chunks.append(get_data(b1500=b1500, channel=top_ch, repetitions=1, points=half_points))
        bottom_chunks.append(get_data(b1500=b1500, channel=bottom_ch, repetitions=1, points=half_points))
        b1500.clear_wgfmu()

    return _stitch(*top_chunks), _stitch(*bottom_chunks)


class WgfmuBaseProcedure(BaseProcedure):
    """Shared parameters and startup for WGFMU-based procedures."""

    mode = ListParameter("Mode", default=SweepMode.DEFAULT.name, choices=[e.name for e in SweepMode])
    pulse_time = FloatParameter("Pulse time", units="s", default=1e-5)

    voltage_top_first = FloatParameter("Top electrode voltage (first)", units="V", default=5.0)
    voltage_top_second = FloatParameter("Top electrode voltage (second)", units="V", default=-5.0)

    top = IntegerParameter("Top channel", default=2)
    current_range = ListParameter(
        "Current range",
        default=WGFMUMeasureCurrentRange.RANGE_100_UA.name,
        choices=[e.name for e in WGFMUMeasureCurrentRange],
    )

    enable_bottom = BooleanParameter("Enable bottom bias and measurement", default=False)

    voltage_bottom_first = FloatParameter(
        "Bottom electrode voltage (first)", units="V", default=-5.0, group_by="enable_bottom"
    )
    voltage_bottom_second = FloatParameter(
        "Bottom electrode voltage (second)", units="V", default=5.0, group_by="enable_bottom"
    )
    bottom = IntegerParameter("Bottom channel", default=1, group_by="enable_bottom")

    advanced_config = BooleanParameter("Advanced config", default=False)

    steps = IntegerParameter("Steps per pulse", default=100, group_by="advanced_config")
    rise_to_hold_ratio = FloatParameter("Rise to hold time ratio", default=1, group_by="advanced_config")

    def startup(self):
        super().startup()
        self.b1500 = connect_instrument(timeout=60000, reset=False)
        self.b1500.clear_wgfmu()
        self.b1500.initialize_wgfmu()

    @property
    def measure_current_range(self) -> WGFMUMeasureCurrentRange:
        return WGFMUMeasureCurrentRange[self.current_range]
