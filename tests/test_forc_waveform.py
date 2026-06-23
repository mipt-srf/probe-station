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
    # No leg-boundary discontinuities: each step advances by one dV grid unit.
    voltage_step = (4.0 - (-4.0)) / 10
    assert np.max(np.abs(np.diff(voltages))) <= voltage_step + 1e-9


def test_splitter_recovers_every_reversal_curve():
    seq, reversal = get_forc_sequence(max_voltage=4.0, min_reversal_voltage=-4.0, grid_steps=10, pulse_time=1e-4)
    _, voltages = seq.to_vectors()

    labels = split_forc_record(voltages, max_voltage=4.0)
    detected = np.unique(labels[~np.isnan(labels)])

    assert np.allclose(np.sort(detected), np.sort(reversal))
    # Lead-in saturation ramp and trailing settle pulse are unlabelled.
    assert np.isnan(labels).any()


def test_invalid_voltage_bounds_raise():
    with pytest.raises(ValueError):
        get_forc_sequence(max_voltage=-1.0, min_reversal_voltage=1.0, grid_steps=10)
