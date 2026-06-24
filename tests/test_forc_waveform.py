"""Unit tests for the FORC waveform builder and per-curve splitter.

These exercise the pure waveform logic only (no instrument), so they run without
hardware or a Qt application.
"""

import numpy as np
import pytest

from probe_station.measurements.wgfmu._waveforms import get_forc_sequence, split_forc_record


def test_reversal_voltages_descend_to_minimum():
    _, reversal = get_forc_sequence(max_voltage=4.0, min_reversal_voltage=-4.0, grid_steps=10, pulse_time=1e-4)

    assert len(reversal) == 10
    # Strictly descending, excluding the degenerate V_r = max_voltage curve, and
    # the deepest curve reaches exactly min_reversal_voltage.
    assert all(earlier > later for earlier, later in zip(reversal, reversal[1:]))
    assert reversal[0] < 4.0
    assert reversal[-1] == pytest.approx(-4.0)


def test_waveform_spans_saturation_and_is_continuous():
    # Drop the trailing settle pulse, whose deliberate return to 0 V is the one
    # legitimate large step in the record.
    seq, _ = get_forc_sequence(
        max_voltage=4.0, min_reversal_voltage=-4.0, grid_steps=10, pulse_time=1e-4, trailing_pulse=False
    )
    _, voltages = seq.to_vectors()
    voltages = np.asarray(voltages, dtype=float)

    assert voltages.min() == pytest.approx(-4.0)
    assert voltages.max() == pytest.approx(4.0)
    # Each leg is a single ramp vector, so the waveform is continuous by having
    # every leg start where the previous one ended (the hardware interpolates the
    # straight line between endpoints).
    for previous, current in zip(seq.pulses, seq.pulses[1:]):
        assert current.start_voltage == pytest.approx(previous.end_voltage)


def test_vector_count_stays_linear_in_grid_steps():
    # A per-step build would grow as grid_steps**2 and overflow the WGFMU vector
    # limit at the default 60; single-vector legs keep it linear.
    seq, _ = get_forc_sequence(max_voltage=4.0, min_reversal_voltage=-4.0, grid_steps=60, pulse_time=2e-4)
    times, _ = seq.to_vectors()
    assert len(times) <= 6 * 60


def _measured_voltage(seq, points):
    """Mimic the instrument's measure event: the interpolated played waveform
    resampled at a uniform time interval (so curves get depth-proportional point
    counts, exactly as the hardware records them)."""
    data = seq.data
    times = np.asarray(data["times"], dtype=float)
    voltages = np.asarray(data["voltages"], dtype=float)
    grid = np.linspace(times.min(), times.max(), points)
    return np.interp(grid, times, voltages)


def test_splitter_recovers_every_reversal_curve():
    seq, reversal = get_forc_sequence(max_voltage=4.0, min_reversal_voltage=-4.0, grid_steps=10, pulse_time=1e-4)
    voltages = _measured_voltage(seq, points=2000)

    labels = split_forc_record(voltages, max_voltage=4.0, reversal_voltages=reversal)
    detected = np.unique(labels[~np.isnan(labels)])

    assert np.allclose(np.sort(detected), np.sort(reversal))
    # Lead-in saturation ramp and trailing settle pulse are unlabelled.
    assert np.isnan(labels).any()


def test_splitter_recovers_curves_for_default_grid():
    # The default 60-curve family, sampled at the default measure-point count.
    seq, reversal = get_forc_sequence(grid_steps=60)
    voltages = _measured_voltage(seq, points=4000)

    labels = split_forc_record(voltages, max_voltage=4.0, reversal_voltages=reversal)
    detected = np.unique(labels[~np.isnan(labels)])

    assert np.allclose(np.sort(detected), np.sort(reversal))


def test_invalid_voltage_bounds_raise():
    with pytest.raises(ValueError):
        get_forc_sequence(max_voltage=-1.0, min_reversal_voltage=1.0, grid_steps=10)
