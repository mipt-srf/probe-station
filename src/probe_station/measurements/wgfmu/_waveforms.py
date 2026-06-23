"""Shared WGFMU helpers for voltage-sweep and cycling procedures."""

import logging
import time
from enum import Enum

import numpy as np
import scipy
from keysight_b1530a._bindings.errors import get_error_summary
from keysight_b1530a.errors import WGFMUError
from waveform_generator import PulseSequence, StaircaseSweep, TrapezoidalPulse, TriangularSweep

from probe_station.measurements.b1500 import (
    B1500,
    WGFMUMeasureCurrentRange,
    WGFMUMeasureEvent,
    WGFMUMeasureMode,
    WGFMUOperationMode,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class SweepMode(Enum):
    DEFAULT = "default"
    PUND = "pund"
    UNIPOLAR = "unipolar"


class WaveformShape(Enum):
    STAIRCASE = "staircase"
    TRIANGLE = "triangle"


WGFMU_TIMING_RESOLUTION = 1e-8
"""Hardware timing grid (10 ns) for both pattern vectors and measure events."""


def _quantize_segment_times(times):
    """Round segment durations to the WGFMU 10 ns grid, as the hardware will.

    The instrument silently rounds every vector duration to the nearest 10 ns,
    so a waveform built from off-grid segments plays for a different time than
    the software computes and the measure event then covers only part of it
    (e.g. a 6 ns segment becomes 10 ns, stretching the sweep). Raise instead of
    letting the hardware distort the waveform.

    Segments that round to zero are dropped by the instrument, not stretched, so
    they are passed through without raising: a high rise-to-hold-ratio sweep is
    deliberately built from long ramp edges and sub-grid holds, and dropping
    those holds yields exactly the intended smooth triangular ramp.
    """
    times = np.asarray(times, dtype=float)
    quantized = np.round(times / WGFMU_TIMING_RESOLUTION) * WGFMU_TIMING_RESOLUTION
    # only a segment that survives on the grid can distort the timing; one that
    # rounds to zero is simply dropped and contributes its (sub-5 ns) duration
    # to neither the software- nor the hardware-computed waveform length
    kept = quantized > 0
    error = np.abs(quantized[kept] - times[kept]) / times[kept]
    bad = error > 0.05
    if np.any(bad):
        worst = np.min(times[kept][bad])
        raise ValueError(
            f"Waveform has segments as short as {worst:.3g} s that cannot be represented "
            f"on the WGFMU 10 ns timing grid; increase the pulse time, reduce the number "
            f"of steps, or adjust the rise to hold ratio"
        )
    return quantized


def on_grid_duration(sequence):
    """Total time the hardware actually plays *sequence*, i.e. the sum of its
    segment durations after rounding each one to the 10 ns grid.

    Use this instead of ``sequence.total_duration`` when another channel's
    waveform must span the same time, otherwise per-segment rounding skews the
    two channels apart.
    """
    times, _ = sequence.to_vectors()
    return float(np.sum(_quantize_segment_times(times)))


def pund_quarter_length(voltages, *, threshold_fraction=0.01):
    """Samples per PUND quarter, excluding the trailing settle pulse.

    A PUND record is the four sweeps (P, U, N, D) followed by the trailing pulse
    that ``get_sequence`` appends to keep the last measured points from being
    clipped. That tail sits at 0 V, so splitting the raw record into four equal
    quarters lets it bleed into the N-D quarter and misaligns the P-U / N-D
    subtraction. Find the last sample still driven above ``threshold_fraction``
    of the peak amplitude, treat everything after as the tail, and divide the
    remaining sweep samples into four quarters.
    """
    magnitude = np.abs(np.asarray(voltages))
    if magnitude.size == 0:
        return 0
    driven = np.where(magnitude > threshold_fraction * magnitude.max())[0]
    sweep_length = int(driven[-1]) + 1 if driven.size else magnitude.size
    return sweep_length // 4


def pund_polarization_current(voltages, currents):
    """P-U / N-D subtracted polarization current, aligned to *currents*.

    Returns an array the same length as *currents*: the P-U hump in the first
    quarter, the N-D hump in the third, and zeros elsewhere (including the
    trailing-pulse tail), so it integrates and plots against the full record
    without the tail distorting the quarter alignment.
    """
    currents = np.asarray(currents)
    quarter = pund_quarter_length(voltages)
    polarization = np.zeros(len(currents))
    if quarter:
        p, u = currents[:quarter], currents[quarter : 2 * quarter]
        n, d = currents[2 * quarter : 3 * quarter], currents[3 * quarter : 4 * quarter]
        polarization[:quarter] = p - u
        polarization[2 * quarter : 3 * quarter] = n - d
    return polarization


def calculate_polarization(times, currents, pad_size_um):
    """Switched polarization 2Pr (uC/cm^2) from a PUND polarization-current trace.

    *currents* must hold both the P-U and N-D subtracted humps; integrating
    |current| over the record sums the positive and negative switched charge
    (2 x 2Pr for a symmetric loop), so the total is halved to report 2Pr.
    """
    charge = scipy.integrate.simpson(y=np.abs(currents), x=times)
    area = (pad_size_um * 1e-4) ** 2
    return charge / area * 1e6 / 2


def get_sequence(
    sequence_type="pund",
    pulse_time=2e-4,
    steps=200,
    first_voltage=4,
    second_voltage=-4,
    rise_to_hold_ratio=0.01,
    *,
    shape=WaveformShape.STAIRCASE.value,
    trailing_pulse: bool = False,
):
    if shape == WaveformShape.TRIANGLE.value:
        # Plateau-free: every per-step interval is a rising edge and the hold is
        # zero, so the staircase collapses into a smooth triangular ramp. The
        # zero-length holds are dropped in set_waveform before reaching the
        # hardware, and rise_to_hold_ratio is irrelevant without holds.
        time_step = 0.0
        edge_time = pulse_time / steps
    else:
        time_step = pulse_time / steps / (1 + rise_to_hold_ratio)
        edge_time = time_step * rise_to_hold_ratio

    first = TriangularSweep(end_voltage=first_voltage, time_step=time_step, steps=steps, edge_time=edge_time)
    second = TriangularSweep(end_voltage=second_voltage, time_step=time_step, steps=steps, edge_time=edge_time)

    if sequence_type == "pund":
        pulses = [first] * 2 + [second] * 2
    elif sequence_type == "unipolar":
        # single unipolar pulse (0 -> first_voltage -> 0); second_voltage is unused
        pulses = [first]
    else:
        pulses = [first, second]
    if trailing_pulse:
        # delay pulse so the last measurement points are not clipped
        pulses.append(
            TrapezoidalPulse(amplitude=0.0, pulse_width=edge_time, rise_time=10 * edge_time, fall_time=edge_time)
        )
    return PulseSequence(pulses)


def get_forc_sequence(
    max_voltage=4.0,
    min_reversal_voltage=-4.0,
    grid_steps=60,
    pulse_time=2e-4,
    *,
    trailing_pulse: bool = True,
):
    """Build one continuous waveform for a first-order reversal curve (FORC) family.

    A FORC measurement is a family of triangular sweeps that all start and end at
    positive saturation ``+max_voltage``. Each curve ramps *down* to a reversal
    voltage ``V_r,i`` and back *up* to ``+max_voltage``; the transient current on
    the ascending branch is what the switching density is later derived from. The
    reversal voltages descend in uniform ``dV`` steps from just below
    ``+max_voltage`` down to ``min_reversal_voltage`` (Schenk et al. 2015,
    *Complex Internal Bias Fields in Ferroelectric Hafnium Oxide*).

    The whole family is chained into a single :class:`PulseSequence` -- successive
    curves share the ``+max_voltage`` endpoint, so they stitch together without
    gaps and the family is measured in one FASTIV run, then split back into curves
    in post-processing (see :func:`split_forc_record`).

    The ramp rate is held constant across the family: every step covers the same
    ``dV`` over the same ``edge_time``, so a deeper curve simply has more steps and
    takes longer. A constant rate keeps the ``E`` (=dE/dt) factor in the switching
    density uniform and makes the per-step voltage grid identical across curves.

    :param max_voltage: Positive saturation voltage; the top of every curve.
    :param min_reversal_voltage: Most negative reversal voltage; the deepest curve.
    :param grid_steps: Number of reversal voltages (and the per-step grid
        resolution of the deepest curve). ``60`` reproduces the paper's 60x60 grid.
    :param pulse_time: Ramp time of the full-depth (deepest) sweep; with the
        constant rate this sets ``edge_time = pulse_time / grid_steps``.
    :param trailing_pulse: Append a 0 V settle pulse so the last measured points
        of the final curve are not clipped.
    :returns: ``(sequence, reversal_voltages)`` -- the chained
        :class:`PulseSequence` and the list of reversal voltages (descending).
    """
    if max_voltage <= min_reversal_voltage:
        raise ValueError("max_voltage must be greater than min_reversal_voltage")
    full_depth = max_voltage - min_reversal_voltage
    voltage_step = full_depth / grid_steps
    edge_time = pulse_time / grid_steps

    # Reversal voltages on the dV grid, descending, excluding the degenerate
    # V_r = max_voltage (zero-depth) curve; the last one equals min_reversal_voltage.
    reversal_voltages = [max_voltage - k * voltage_step for k in range(1, grid_steps + 1)]

    # Each leg is a single monotonic ramp (StaircaseSweep), not a there-and-back
    # triangle. PulseSequence concatenates the legs' absolute voltages, so every
    # leg's start_voltage is pinned to the previous leg's endpoint to keep the
    # waveform continuous. time_step=0 makes each step a pure ramp edge of
    # edge_time, so the rate (dV per edge_time) is constant across the family.
    def ramp(start, end, steps):
        return StaircaseSweep(start_voltage=start, end_voltage=end, time_step=0.0, steps=steps, edge_time=edge_time)

    # Initial saturation ramp 0 -> +max_voltage at the same per-step rate.
    lead_steps = max(round(max_voltage / voltage_step), 1)
    pulses = [ramp(0.0, max_voltage, lead_steps)]
    for k, reversal_voltage in enumerate(reversal_voltages, start=1):
        # Down to the reversal voltage, then back up to saturation; both legs
        # span k grid steps so each step covers exactly one dV.
        pulses.append(ramp(max_voltage, reversal_voltage, k))
        pulses.append(ramp(reversal_voltage, max_voltage, k))
    if trailing_pulse:
        pulses.append(
            TrapezoidalPulse(amplitude=0.0, pulse_width=edge_time, rise_time=10 * edge_time, fall_time=edge_time)
        )
    return PulseSequence(pulses), reversal_voltages


def split_forc_record(voltages, *, max_voltage):
    """Label each sample with the reversal voltage of the FORC it belongs to.

    The continuous FORC record (see :func:`get_forc_sequence`) is one saturation
    ramp followed by N down-up reversal sweeps that all peak at ``+max_voltage``.
    Those peaks bound the individual curves; the minimum voltage between two
    consecutive peaks is that curve's reversal voltage. Samples in the leading
    saturation ramp (before the first peak) and in the trailing settle pulse
    (after the last peak) are not part of any curve and are labelled ``NaN``.

    Splitting on the measured voltage rather than on the constructed sample
    indices keeps the labelling robust against the hardware's 10 ns timing-grid
    rounding and any measure-point decimation.

    :param voltages: Measured top-electrode voltage of the whole FORC record.
    :param max_voltage: Positive saturation voltage (the peak value).
    :returns: ``float`` array, same length as *voltages*, holding each sample's
        reversal voltage (``NaN`` for the lead-in and trailing samples).
    """
    from scipy.signal import find_peaks

    v = np.asarray(voltages, dtype=float)
    span = max_voltage - v.min()
    # Peaks are the saturation turning points; require near-full height and a
    # prominence well above noise so only the true +max_voltage tops are found.
    peaks, _ = find_peaks(v, height=0.9 * max_voltage, prominence=0.25 * span)
    labels = np.full(v.size, np.nan)
    for start, stop in zip(peaks[:-1], peaks[1:]):
        labels[start:stop] = v[start:stop].min()
    return labels


def get_constant_sequence(voltage, duration, edge_time=None):
    """A flat-top pulse holding *voltage* for *duration* seconds.

    Used to bias a second WGFMU channel at a constant level while another
    channel sweeps (e.g. a FET drain held at Vds during a gate sweep). The
    short rise/fall edges keep the total duration equal to *duration* so the
    measure points stay time-aligned with the sweeping channel.
    """
    if edge_time is None:
        # snap the auto edge to the 10 ns timing grid: duration/1000 is an
        # arbitrary fraction that can land between grid points (e.g. 21.2 ns
        # for a ~21 us waveform) and then fail the quantization tolerance
        edge_time = max(
            round(duration / 1000 / WGFMU_TIMING_RESOLUTION) * WGFMU_TIMING_RESOLUTION,
            WGFMU_TIMING_RESOLUTION,
        )
    pulse_width = duration - 2 * edge_time
    if pulse_width <= 0:
        raise ValueError(f"Duration {duration:.3g} s is too short for {edge_time:.3g} s rise/fall edges")
    return PulseSequence(
        [TrapezoidalPulse(amplitude=voltage, pulse_width=pulse_width, rise_time=edge_time, fall_time=edge_time)]
    )


def set_waveform(
    b1500: B1500,
    sequence,
    *,
    repetitions=1,
    channel=1,
    measure=True,
    measure_points=1600,
    pattern_name="sequence",
):
    pattern_name += f"_wgfmu{channel}"
    b1500.create_wgfmu_pattern(pattern_name, sequence.pulses[0].dc_bias)
    times, voltages = sequence.to_vectors()
    times = _quantize_segment_times(times)
    # WGFMU_addVectors rejects any vector shorter than the 10 ns grid as "out of
    # range" (B1530A reference, addVector/addVectors), so a sub-grid hold would
    # be silently skipped by the hardware. Drop those segments here instead: the
    # preceding ramp already reaches the same voltage, so the waveform is
    # unchanged, and we never hand an out-of-range duration to the library.
    keep = times > 0
    times = times[keep]
    voltages = np.asarray(voltages)[keep]
    # sum the on-grid segments instead of sequence.total_duration so the
    # measure event spans exactly what the hardware plays
    seq_time = float(np.sum(times))
    logger.info(
        f"Waveform for {pattern_name}: {len(voltages)} samples, {seq_time:.6g} s, {len(sequence.pulses)} pulses"
    )
    b1500.add_vectors_to_wgfmu_pattern(pattern_name, times.tolist(), voltages.tolist())
    if measure:
        interval = np.floor(seq_time / measure_points / WGFMU_TIMING_RESOLUTION) * WGFMU_TIMING_RESOLUTION
        if interval < WGFMU_TIMING_RESOLUTION:
            raise ValueError(
                f"{measure_points} measure points do not fit into the {seq_time:.3g} s waveform "
                f"at the WGFMU 10 ns sampling resolution; reduce the number of points to plot"
            )
        b1500.set_wgfmu_measure_event(
            pattern_name=pattern_name,
            event_name="event",
            points=measure_points,
            interval=interval,
            average=min(interval, 0.02),  # averaging time is capped at ~20 ms by hardware
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
    measure_ranges: dict[int, WGFMUMeasureCurrentRange] | None = None,
    configure_measure_mode: bool = True,
):
    if channels is None:
        channels = [2]
    measure_ranges = measure_ranges or {}
    for channel in channels:
        wgfmu = b1500.wgfmus[channel]
        wgfmu.set_operation_mode(mode)
        if configure_measure_mode:
            wgfmu.set_measure_mode(WGFMUMeasureMode.CURRENT)
            # per-channel range when given (e.g. a bottom electrode that needs a
            # different range than the top), otherwise the common measure_range
            wgfmu.set_measure_current_range(measure_ranges.get(channel, measure_range))
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
        logger.debug(f"Raw data length: {len(voltages)}")
        return times, voltages, currents

    times = np.split(np.array(times), repetitions)[-1]
    currents = np.split(np.array(currents), repetitions)[-1]
    voltages = np.split(np.array(voltages), repetitions)[-1]
    logger.debug(f"Raw voltage array length (last rep): {len(voltages)}")

    times = np.mean(times.reshape(-1, len(voltages) // points), axis=1)
    currents = np.mean(currents.reshape(-1, len(voltages) // points), axis=1)
    voltages = np.mean(voltages.reshape(-1, len(voltages) // points), axis=1)
    logger.debug(f"Decimated voltage array length: {len(voltages)}")

    return times, voltages, currents


def run_waveforms(
    b1500: B1500,
    *,
    top_seq,
    top_ch: int,
    bottom_seq=None,
    bottom_ch: int | None = None,
    repetitions: int,
    current_range: WGFMUMeasureCurrentRange | None = None,
    bottom_current_range: WGFMUMeasureCurrentRange | None = None,
    measure: bool,
    plot_points: int | None = None,
):
    """Set waveforms on top (and optional bottom), run, optionally fetch data.

    Returns ``None`` when ``measure`` is False; otherwise returns
    ``(top_data, bottom_data)`` where each entry is ``(times, voltages, currents)``
    (and ``bottom_data`` is ``None`` when no bottom channel is provided).

    ``bottom_current_range`` overrides ``current_range`` on the bottom channel
    only; when omitted the bottom channel shares ``current_range``.

    ``current_range`` is only applied when ``measure`` is True; callers that do
    not measure (e.g. cycling) may omit it.
    """
    set_waveform(
        b1500=b1500,
        sequence=top_seq,
        repetitions=repetitions,
        channel=top_ch,
        measure=measure,
        measure_points=plot_points or 0,
    )
    if bottom_seq is not None:
        set_waveform(
            b1500=b1500,
            sequence=bottom_seq,
            repetitions=repetitions,
            channel=bottom_ch,
            measure=measure,
            measure_points=plot_points or 0,
        )

    channels = [top_ch] if bottom_ch is None else [top_ch, bottom_ch]
    measure_ranges = None
    if bottom_ch is not None and bottom_current_range is not None:
        measure_ranges = {top_ch: current_range, bottom_ch: bottom_current_range}
    try:
        run(
            b1500=b1500,
            channels=channels,
            measure_range=current_range,
            measure_ranges=measure_ranges,
            configure_measure_mode=measure,
        )
    except WGFMUError:
        logger.error(f"{get_error_summary()}")
        b1500.clear_wgfmu()
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
    bottom_current_range: WGFMUMeasureCurrentRange | None = None,
    plot_points: int,
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
    for i, (name, half_top, half_bot) in enumerate(halves):
        set_waveform(
            b1500=b1500,
            sequence=half_top,
            repetitions=1,
            channel=top_ch,
            measure=True,
            measure_points=half_points,
            pattern_name=f"top_{name}",
        )
        set_waveform(
            b1500=b1500,
            sequence=half_bot,
            repetitions=1,
            channel=bottom_ch,
            measure=True,
            measure_points=half_points,
            pattern_name=f"bottom_{name}",
        )
        measure_ranges = None
        if bottom_current_range is not None:
            measure_ranges = {top_ch: current_range, bottom_ch: bottom_current_range}
        try:
            run(
                b1500=b1500,
                channels=[top_ch, bottom_ch],
                measure_range=current_range,
                measure_ranges=measure_ranges,
                configure_measure_mode=True,
            )
        except WGFMUError:
            logger.error(f"{get_error_summary()}")
            b1500.clear_wgfmu()
            raise

        top_data = get_data(b1500=b1500, channel=top_ch, repetitions=1, points=half_points)
        bottom_data = get_data(b1500=b1500, channel=bottom_ch, repetitions=1, points=half_points)

        run_start = time.perf_counter()
        if i == 0:
            first_run_start = run_start
            b1500.clear_wgfmu()
        else:
            shift = run_start - first_run_start
            logger.info(f"Inter-half delay before {name}: {shift:.4f} s")
            top_data = (top_data[0] + shift, top_data[1], top_data[2])
            bottom_data = (bottom_data[0] + shift, bottom_data[1], bottom_data[2])

        top_chunks.append(top_data)
        bottom_chunks.append(bottom_data)

    return _stitch(*top_chunks), _stitch(*bottom_chunks)
