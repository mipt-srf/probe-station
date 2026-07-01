"""Batch analysis for the ``fet_ids_vds_vg`` output-characteristics experiment.

:mod:`probe_station.experiments.fet_ids_vds_vg` records one Ids(Vds) sweep per
gate voltage, saving each as its own PyMeasure CSV (suffixed with the gate
voltage).  This module reassembles such a folder into a single tidy
:class:`pandas.DataFrame` and draws the standard output- and
transfer-characteristic plots.

Typical use::

    from probe_station.analysis import fet_ids_vds_vg as oc

    data = oc.load(folder)
    oc.plot_output(data)  # Ids(Vds) family, coloured by Vg
    oc.plot_output(data, logy=True)  # same, log |Ids|
    oc.plot_transfer(data, [-0.5, 0.5])  # |Ids|(Vg) at fixed Vds
"""

import logging
from collections.abc import Iterable
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd

from probe_station.analysis.dataset import Dataset
from probe_station.analysis.utilities import get_colormap

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

#: Column names of the tidy DataFrame returned by :func:`load`.
V_GATE = "Gate voltage, V"
V_DS = "Drain-source voltage, V"
I_DS = "Drain current, A"


def _truncated(name: str, lo: float, hi: float, n: int = 256):
    """Return a smooth colormap covering only the ``[lo, hi]`` span of *name*."""
    base = matplotlib.colormaps[name]
    return matplotlib.colors.LinearSegmentedColormap.from_list(f"{name}_{lo}_{hi}", base(np.linspace(lo, hi, n)))


#: Colormap for few-curve comparisons (plasma with its bright-yellow end trimmed).
#: The default violet->yellow gradient reads well with many curves, but its pale
#: yellow is hard to see with only a few; pass this as ``cmap=`` in that case.
COMPARISON_CMAP = _truncated("plasma", 0.0, 0.85)


def _file_index(path: Path) -> int:
    """Leading integer in the file name = acquisition order."""
    return int(path.name.split("_", 1)[0])


def get_files(folder: str | Path, ignore: Iterable[int] = ()) -> list[Path]:
    """Return the experiment's CSV sweeps, ordered by acquisition index.

    :param folder: Folder produced by the ``fet_ids_vds_vg`` experiment.
    :param ignore: Acquisition indexes (file name prefixes) to skip.
    """
    ignore = set(ignore)
    files = sorted(Path(folder).glob("*.csv"), key=_file_index)
    return [f for f in files if _file_index(f) not in ignore]


def load(folder: str | Path, ignore: Iterable[int] = ()) -> pd.DataFrame:
    """Load every Ids(Vds) sweep in *folder* into one tidy DataFrame.

    Columns are :data:`V_GATE`, :data:`V_DS` and :data:`I_DS`.

    :param folder: Folder produced by the ``fet_ids_vds_vg`` experiment.
    :param ignore: Acquisition indexes (file name prefixes) to skip.
    """
    frames = []
    for file in get_files(folder, ignore):
        ds = Dataset(file)
        frames.append(
            pd.DataFrame(
                {
                    V_GATE: ds.gate_voltage,
                    V_DS: ds.vds.to_numpy(),
                    I_DS: ds.ids.to_numpy(),
                }
            )
        )
    data = pd.concat(frames, ignore_index=True)
    logger.info("Loaded %d Ids(Vds) sweeps from %s", len(frames), folder)
    return data


def _param_colormap(values: np.ndarray, cmap=None, *, log: bool = False):
    """Build the colormap and normalisation for colouring curves by a parameter.

    :param values: The parameter values that will be mapped to colours.
    :param cmap: Colormap name or instance (default violet->yellow).
    :param log: Use a logarithmic colour scale (only positive values are
        representable; callers should clamp non-positive values before mapping).
    :return: A ``(cmap, norm)`` tuple.
    """
    values = np.asarray(values)
    if cmap is None:
        cmap = get_colormap("Blueviolet", "Yellow", len(np.unique(values)))
    elif isinstance(cmap, str):
        cmap = matplotlib.colormaps[cmap]
    if log:
        positive = values[values > 0]
        norm = matplotlib.colors.LogNorm(positive.min(), values.max())
    else:
        norm = plt.Normalize(values.min(), values.max())
    return cmap, norm


def plot_output(
    data: pd.DataFrame,
    cmap=None,
    ax: plt.Axes | None = None,
    *,
    logy: bool = False,
    log_gate: bool = False,
    linewidth: float = 1.2,
    alpha: float | None = None,
) -> plt.Axes:
    """Plot the output-characteristic family Ids(Vds), one curve per gate voltage.

    :param data: Tidy DataFrame from :func:`load`.
    :param cmap: Colormap (name or instance) for the gate-voltage gradient
        (default violet->yellow).
    :param ax: Existing axes to draw on; a new figure is created when ``None``.
    :param logy: Plot ``|Ids|`` on a logarithmic axis when ``True``.
    :param log_gate: Colour the curves on a logarithmic gate-voltage scale, which
        spreads the closely-spaced low-Vg curves apart. Curves at ``Vg <= 0`` are
        drawn in the lowest colour.
    :param linewidth: Width of each sweep line.
    :param alpha: Line transparency (0-1); ``None`` is fully opaque.
    :return: The axes the family was drawn on.
    """
    gates = np.sort(data[V_GATE].unique())
    cmap, norm = _param_colormap(gates, cmap, log=log_gate)
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 6))
    for gate in gates:
        sweep = data[data[V_GATE] == gate]
        current = sweep[I_DS].abs() if logy else sweep[I_DS]
        color = cmap(norm(np.clip(gate, norm.vmin, norm.vmax)))
        ax.plot(sweep[V_DS], current, color=color, lw=linewidth, alpha=alpha)
    ax.set_xlabel(V_DS)
    if logy:
        ax.set_ylabel(r"$|$Drain current$|$, A")
        ax.set_yscale("log")
    else:
        ax.set_ylabel(I_DS)
        ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    fig = ax.figure
    assert fig is not None
    cbar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, label=V_GATE)
    if log_gate:
        _label_log_colorbar(cbar)
    return ax


def _label_log_colorbar(cbar) -> None:
    """Label only round 1/3-per-decade values on a log colorbar, blanking the rest.

    A default log colorbar tick-labels every minor tick (2, 3, ... 9), which is
    unreadable for a gate-voltage gradient; this keeps a handful of clean labels.
    """
    vmin, vmax = cbar.norm.vmin, cbar.norm.vmax
    decades = range(int(np.floor(np.log10(vmin))), int(np.ceil(np.log10(vmax))) + 1)
    labeled = [m * 10.0**d for d in decades for m in (1, 3)]
    labeled = [t for t in labeled if vmin <= t <= vmax]

    def fmt(value, _pos):
        return f"{value:g}" if np.isclose(value, labeled, rtol=1e-2).any() else ""

    formatter = matplotlib.ticker.FuncFormatter(fmt)
    cbar.ax.yaxis.set_major_formatter(formatter)
    cbar.ax.yaxis.set_minor_formatter(formatter)


def transfer_curve(data: pd.DataFrame, vds: float) -> pd.DataFrame:
    """Return drain current versus gate voltage at a fixed Vds.

    Each sweep is interpolated to *vds* after averaging its forward and reverse
    branches.

    :param data: Tidy DataFrame from :func:`load`.
    :param vds: Drain-source voltage at which to slice the family.
    :return: DataFrame with columns :data:`V_GATE` and :data:`I_DS`, sorted by Vg.
    """
    rows = []
    for gate, sweep in data.groupby(V_GATE):
        branch_mean = sweep.groupby(sweep[V_DS].round(4))[I_DS].mean()
        current = np.interp(
            vds,
            branch_mean.index.to_numpy(),
            branch_mean.to_numpy(),
            left=np.nan,
            right=np.nan,
        )
        rows.append((gate, current))
    return pd.DataFrame(rows, columns=pd.Index([V_GATE, I_DS])).sort_values(V_GATE, ignore_index=True)


def plot_transfer(
    data: pd.DataFrame,
    vds_values: float | Iterable[float],
    ax: plt.Axes | None = None,
    *,
    alpha: float | None = None,
) -> plt.Axes:
    """Plot transfer characteristics ``|Ids|(Vg)`` at one or more Vds values.

    :param data: Tidy DataFrame from :func:`load`.
    :param vds_values: Drain-source voltage(s) at which to slice the family.
    :param ax: Existing axes to draw on; a new figure is created when ``None``.
    :param alpha: Line transparency (0-1); ``None`` is fully opaque.
    :return: The axes the curves were drawn on.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 6))
    vds_array = np.fromiter(vds_values, dtype=float) if isinstance(vds_values, Iterable) else np.array([vds_values])
    for vds in vds_array:
        curve = transfer_curve(data, vds)
        ax.plot(curve[V_GATE], curve[I_DS].abs(), "o-", ms=3, label=f"{vds:g} V", alpha=alpha)
    ax.set_xlabel(V_GATE)
    ax.set_ylabel(r"$|$Drain current$|$, A")
    ax.set_yscale("log")
    ax.legend(title="Drain-source voltage")
    return ax


def _vds_colors(vds_values: np.ndarray, cmap, *, log: bool, discrete: bool):
    """Resolve curve colours and a matching colorbar mappable for Vds slices.

    :param vds_values: Sorted Vds values, one per curve.
    :param cmap: Colormap name or instance.
    :param log: Continuous logarithmic colour scale (ignored when *discrete*).
    :param discrete: One distinct colour band per value, ticked at the values --
        honest for a handful of slices, where a continuous bar implies a
        non-existent continuum.
    :return: ``(colors, mappable, ticks)``; *ticks* is ``None`` when continuous.
    """
    n = len(vds_values)
    if discrete:
        base, _ = _param_colormap(vds_values, cmap)
        colors = base(np.linspace(0, 1, n)) if n > 1 else base([0.5])
        listed = matplotlib.colors.ListedColormap(colors)
        if n > 1:
            edges = (vds_values[:-1] + vds_values[1:]) / 2
            bounds = np.concatenate(([2 * vds_values[0] - edges[0]], edges, [2 * vds_values[-1] - edges[-1]]))
        else:
            bounds = np.array([vds_values[0] - 0.5, vds_values[0] + 0.5])
        mappable = matplotlib.cm.ScalarMappable(norm=matplotlib.colors.BoundaryNorm(bounds, listed.N), cmap=listed)
        return colors, mappable, vds_values
    cmap, norm = _param_colormap(vds_values, cmap, log=log)
    colors = [cmap(norm(np.clip(v, norm.vmin, norm.vmax))) for v in vds_values]
    return colors, matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap), None


def plot_transfer_family(
    data: pd.DataFrame,
    vds_values: Iterable[float] | None = None,
    cmap=None,
    ax: plt.Axes | None = None,
    *,
    n_curves: int = 40,
    log_vds: bool = False,
    discrete: bool | None = None,
    linewidth: float = 1.2,
    alpha: float | None = None,
    linestyle: str = "-",
    label: str | None = None,
    colorbar: bool = True,
) -> plt.Axes:
    """Plot transfer characteristics ``|Ids|(Vg)`` as a family coloured by Vds.

    The drain-voltage counterpart of :func:`plot_output`: one transfer curve per
    Vds value, coloured from violet (low Vds) to yellow (high Vds).

    To overlay two devices on a shared Vds scale, call twice on the same axes,
    giving each a *label* and *linestyle* and suppressing the duplicate colorbar::

        ax = oc.plot_transfer_family(fet, vds_values=v_ds, label="FET", linestyle="--")
        oc.plot_transfer_family(fefet, vds_values=v_ds, ax=ax, label="FeFET", colorbar=False)

    :param data: Tidy DataFrame from :func:`load`.
    :param vds_values: Drain-source voltages to slice at; defaults to *n_curves*
        values spanning the measured Vds range.
    :param cmap: Colormap (name or instance) for the Vds gradient.
    :param ax: Existing axes to draw on; a new figure is created when ``None``.
    :param n_curves: Number of evenly-spaced Vds slices when *vds_values* is None.
    :param log_vds: Colour the curves on a logarithmic Vds scale (positive Vds
        only; curves at ``Vds <= 0`` are drawn in the lowest colour).
    :param discrete: Use a discrete colorbar (one swatch per Vds, ticked at the
        values) instead of a continuous gradient. ``None`` chooses automatically:
        discrete for a few slices (<= 15), continuous otherwise.
    :param linewidth: Width of each transfer line.
    :param alpha: Line transparency (0-1); ``None`` is fully opaque.
    :param linestyle: Line style for this family (e.g. ``"--"`` for an overlay).
    :param label: Legend label for this family (one entry, not per curve).
    :param colorbar: Add the Vds colorbar; set ``False`` on overlay calls.
    :return: The axes the family was drawn on.
    """
    if vds_values is None:
        vds_array = np.linspace(data[V_DS].min(), data[V_DS].max(), n_curves)
    else:
        vds_array = np.fromiter(vds_values, dtype=float)
    vds_array = np.sort(vds_array)
    if discrete is None:
        discrete = len(vds_array) <= 15
    colors, mappable, ticks = _vds_colors(vds_array, cmap, log=log_vds, discrete=discrete)
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 6))
    for vds, color in zip(vds_array, colors):
        curve = transfer_curve(data, vds)
        ax.plot(curve[V_GATE], curve[I_DS].abs(), color=color, lw=linewidth, alpha=alpha, ls=linestyle)
    ax.set_xlabel(V_GATE)
    ax.set_ylabel(r"$|$Drain current$|$, A")
    ax.set_yscale("log")
    if label is not None:
        # One neutral proxy entry per family (the curves themselves are unlabelled).
        ax.plot([], [], color="0.3", lw=linewidth, ls=linestyle, label=label)
        ax.legend()
    if colorbar:
        fig = ax.figure
        assert fig is not None
        cbar = fig.colorbar(mappable, ax=ax, label=V_DS, ticks=ticks)
        if discrete:
            cbar.ax.set_yticklabels([f"{v:g}" for v in ticks])
        elif log_vds:
            _label_log_colorbar(cbar)
    return ax
