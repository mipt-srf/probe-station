"""Unit tests for the FORC switching-density handler.

These build a synthetic FORC family with a single known Preisach hysteron and
check that the recovered switching density peaks at the expected reversal and
switching fields. No instrument or saved file is required.
"""

import numpy as np
import pandas as pd
import pytest

from probe_station.analysis.handlers.forc import Forc


class _Parent:
    """Minimal stand-in for the Dataset/Results parent a handler wraps."""

    def __init__(self, data, parameters):
        self.data = data
        self.parameters = parameters


def _make_forc_family(
    switching_field=2.0,
    backswitching_field=-1.0,
    max_voltage=4.0,
    min_reversal_voltage=-4.0,
    n_curves=40,
    samples=60,
    charging=2e-8,
):
    """Long-form FORC data for one hysteron (switching_field, backswitching_field).

    The hysteron contributes a Gaussian switching-current bump at ``E ==
    switching_field`` on the ascending branch, but only for curves whose reversal
    voltage went at or below ``backswitching_field`` (i.e. the hysteron was
    backswitched and can switch again on the way up). A linear charging current
    common to every curve is added to verify it cancels in the d/dE_r derivative.
    """
    reversal_voltages = np.linspace(max_voltage, min_reversal_voltage, n_curves + 1)[1:]
    width = 0.25
    rows = {"Reversal Voltage": [], "Top Electrode Voltage": [], "Top Electrode Current": [], "Time": []}
    t = 0.0
    dt = 1e-5
    for reversal in reversal_voltages:
        down = np.linspace(max_voltage, reversal, samples)
        up = np.linspace(reversal, max_voltage, samples)
        voltages = np.concatenate([down, up])
        ascending = np.arange(voltages.size) >= samples
        current = charging * voltages
        if reversal <= backswitching_field:
            current = current + ascending * np.exp(-((voltages - switching_field) ** 2) / (2 * width**2))
        for v, i in zip(voltages, current):
            rows["Reversal Voltage"].append(reversal)
            rows["Top Electrode Voltage"].append(v)
            rows["Top Electrode Current"].append(i)
            rows["Time"].append(t)
            t += dt
    return pd.DataFrame(rows)


def _handler(**kwargs):
    data = _make_forc_family(**kwargs)
    return Forc(_Parent(data, {"max_voltage": 4.0, "min_reversal_voltage": -4.0, "pulse_time": 2e-4}))


def test_density_is_triangular():
    reversal, e_grid, rho = _handler().switching_density()

    e_mesh, reversal_mesh = np.meshgrid(e_grid, reversal)
    # Below the diagonal (E < E_r) is unmeasured and must be NaN; the rest finite.
    assert np.all(np.isnan(rho[e_mesh < reversal_mesh - 1e-9]))
    assert np.isfinite(rho[e_mesh > reversal_mesh + 0.5]).any()


def test_density_peaks_at_the_hysteron():
    handler = _handler(switching_field=2.0, backswitching_field=-1.0)
    reversal, e_grid, rho = handler.switching_density(smooth=1.0)

    peak_row, peak_col = np.unravel_index(np.nanargmax(rho), rho.shape)
    assert reversal[peak_row] == pytest.approx(-1.0, abs=0.6)
    assert e_grid[peak_col] == pytest.approx(2.0, abs=0.6)


def test_ramp_rate_from_record_is_positive():
    rate = _handler().ramp_rate()
    assert rate > 0


def test_density_needs_two_curves():
    data = _make_forc_family(n_curves=1)
    with pytest.raises(ValueError):
        Forc(_Parent(data, {})).switching_density()
