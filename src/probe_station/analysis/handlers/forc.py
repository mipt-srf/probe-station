"""Handler for first-order reversal curve (FORC) analysis.

Derives the experimental Preisach / switching-density plot from a FORC family
recorded by :class:`~probe_station.measurements.wgfmu.forc.WgfmuForcProcedure`.
The stored data is in long form -- one row per sample, tagged with the reversal
voltage of the curve it belongs to -- so it is first pivoted back into the family
of ascending branches ``j(E_r, E)``, then differentiated across the reversal
field to obtain the switching density (Schenk et al. 2015, *Complex Internal Bias
Fields in Ferroelectric Hafnium Oxide*, eq 1):

    rho(E_r, E) = (1 / 2E') * d j_FORC(E_r, E) / d E_r

where ``j_FORC`` is the transient current on the ascending branch (sweeping up
from the reversal voltage back to saturation) and ``E'`` (=dE/dt) is the ramp
rate, held constant by the waveform. Differentiating across reversal curves
cancels the leakage and linear-charging current common to every curve at a given
field, isolating the switching contribution.
"""

import numpy as np
from matplotlib import pyplot as plt

from probe_station.analysis.handlers.base import BaseHandler


class Forc(BaseHandler):
    """Switching-density (experimental Preisach) analysis of a FORC family."""

    REVERSAL_COLUMN = "Reversal Voltage"
    VOLTAGE_COLUMN = "Top Electrode Voltage"
    CURRENT_COLUMN = "Top Electrode Current"
    TIME_COLUMN = "Time"

    def _param(self, name, default=None):
        """Read a procedure parameter as a plain value (unwrapping ``Parameter``)."""
        value = self.parameters.get(name, default)
        return getattr(value, "value", value)

    def ascending_branches(self):
        """Return the ascending branch of every reversal curve.

        Each recorded curve sweeps down from saturation to its reversal voltage
        and back up; only the ascending leg (reversal -> saturation) carries the
        switching information used for the density. Returns a list of
        ``(reversal_voltage, voltage, current)`` tuples with *voltage* sorted
        ascending, ordered by reversal voltage from most negative to most
        positive.
        """
        branches = []
        for reversal, group in self.data.groupby(self.REVERSAL_COLUMN, sort=True):
            voltage = group[self.VOLTAGE_COLUMN].to_numpy()
            current = group[self.CURRENT_COLUMN].to_numpy()
            # The reversal point is the lowest voltage in the curve; everything
            # after it is the ascending branch back to saturation.
            turn = int(np.argmin(voltage))
            voltage_asc = voltage[turn:]
            current_asc = current[turn:]
            order = np.argsort(voltage_asc)
            branches.append((float(reversal), voltage_asc[order], current_asc[order]))
        return branches

    def ramp_rate(self):
        """Field ramp rate ``E' = dE/dt`` (V/s), estimated from the record.

        Uses the median absolute slope of voltage vs time across the whole
        record (robust to the few reversal turning points), falling back to the
        procedure parameters if no usable timing is stored.
        """
        if self.TIME_COLUMN in self.data:
            time = self.data[self.TIME_COLUMN].to_numpy()
            voltage = self.data[self.VOLTAGE_COLUMN].to_numpy()
            dt = np.diff(time)
            good = dt > 0
            rates = np.abs(np.diff(voltage)[good] / dt[good])
            rates = rates[np.isfinite(rates) & (rates > 0)]
            if rates.size:
                return float(np.median(rates))
        span = abs(self._param("max_voltage", 1.0) - self._param("min_reversal_voltage", -1.0))
        return span / self._param("pulse_time", 1.0)

    def switching_density(self, e_points: int | None = None, smooth: float | None = None):
        """Compute the switching density ``rho(E_r, E)`` on a regular grid.

        :param e_points: Number of points on the switching-field (E) axis;
            defaults to the number of reversal curves (a square grid).
        :param smooth: If given, the standard deviation (in grid cells) of a
            NaN-aware Gaussian smoothing applied to the density, analogous to the
            polynomial smoothing used in the paper.
        :returns: ``(reversal, e_grid, rho)`` -- the reversal-field axis
            (ascending), the switching-field axis, and the density as a 2D array
            ``rho[reversal, e]``. Cells above the diagonal ``E < E_r`` (outside
            the measured triangle) are ``NaN``.
        """
        branches = self.ascending_branches()
        if len(branches) < 2:
            raise ValueError("FORC density needs at least two reversal curves")

        reversal = np.array([branch[0] for branch in branches])
        v_max = max(branch[1].max() for branch in branches)
        if e_points is None:
            e_points = len(branches)
        e_grid = np.linspace(reversal.min(), v_max, e_points)

        # j(E_r, E): interpolate each ascending branch onto the common E grid,
        # leaving the unmeasured region below the reversal voltage (E < E_r) NaN.
        current = np.full((len(branches), e_points), np.nan)
        for row, (reversal_voltage, voltage_asc, current_asc) in enumerate(branches):
            covered = e_grid >= reversal_voltage
            current[row, covered] = np.interp(e_grid[covered], voltage_asc, current_asc)

        rho = np.gradient(current, reversal, axis=0) / (2 * self.ramp_rate())

        # The absolute sign depends on the electrode-current wiring convention;
        # orient so the dominant switching feature reads positive.
        if np.nanmax(rho) < -np.nanmin(rho):
            rho = -rho

        if smooth:
            rho = _gaussian_smooth_nan(rho, smooth)
        return reversal, e_grid, rho

    def plot_curves(self, alpha: float = 0.5) -> None:
        """Overlay the raw transient-current FORC family (current vs voltage)."""
        for _, group in self.data.groupby(self.REVERSAL_COLUMN, sort=True):
            self.plot_base(
                group[self.VOLTAGE_COLUMN],
                group[self.CURRENT_COLUMN],
                xlabel="Voltage, V",
                ylabel="Current, A",
                alpha=alpha,
            )

    def plot_density(
        self,
        e_points: int | None = None,
        smooth: float | None = None,
        coordinates: str = "reversal",
        cmap: str = "jet",
    ) -> None:
        """Plot the switching density as a pseudocolour map.

        :param coordinates: ``"reversal"`` plots density over (switching field E,
            reversal field E_r); ``"coercive"`` applies the standard transform
            ``E_c = (E - E_r) / 2``, ``E_bias = (E + E_r) / 2`` and plots over
            (coercive field, bias field).
        :param cmap: Matplotlib colormap name.
        """
        reversal, e_grid, rho = self.switching_density(e_points=e_points, smooth=smooth)

        plt.style.use(["science", "no-latex", "notebook"])
        e_mesh, reversal_mesh = np.meshgrid(e_grid, reversal)
        if coordinates == "coercive":
            x = (e_mesh - reversal_mesh) / 2
            y = (e_mesh + reversal_mesh) / 2
            xlabel, ylabel = "Coercive field $E_c$, V", "Bias field $E_{bias}$, V"
        elif coordinates == "reversal":
            x, y = e_mesh, reversal_mesh
            xlabel, ylabel = "Switching field $E$, V", "Reversal field $E_r$, V"
        else:
            raise ValueError(f"Unknown coordinates {coordinates!r}; use 'reversal' or 'coercive'")

        mesh = plt.pcolormesh(x, y, np.ma.masked_invalid(rho), shading="auto", cmap=cmap)
        plt.colorbar(mesh, label=r"Switching density $\rho$, A$\cdot$s/V$^2$")
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)


def _gaussian_smooth_nan(values: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian-smooth *values*, ignoring (and preserving) NaN cells.

    Smooths the data and a validity mask separately and divides, so NaN cells
    (the unmeasured region above the diagonal) neither contribute to nor are
    filled by the smoothing.
    """
    from scipy.ndimage import gaussian_filter

    valid = np.isfinite(values).astype(float)
    filled = np.where(valid > 0, values, 0.0)
    smoothed = gaussian_filter(filled, sigma=sigma)
    weight = gaussian_filter(valid, sigma=sigma)
    with np.errstate(invalid="ignore", divide="ignore"):
        result = smoothed / weight
    result[valid == 0] = np.nan
    return result
