"""Module contains utility functions for the probe station project."""

import logging
from collections.abc import Generator
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import scienceplots  # noqa: F401
from colour import Color
from labellines import labelLines
from scipy.interpolate import interp1d

from probe_station.dataset import Dataset

plt.style.use(["science", "no-latex", "notebook"])
logging.basicConfig(level=logging.INFO)


def get_files_in_folder(path: str, ignore: tuple = ()) -> Generator[Path, None, None]:
    """Get data file paths in the specified directory, excluding ignored indexes.

    :param path: Path to the directory containing data files.
    :param ignore: Tuple of file indexes to ignore.
    :return: Generator of data file paths.
    """
    datafile_paths = list(Path(path).glob("*.data"))
    indexes = set(range(1, len(datafile_paths) + 1)) - set(ignore)
    yield from (Path(path) / f"{df_index}.data" for df_index in indexes)


def get_color_gradient(from_color: str, to_color: str, count: int) -> Generator[str, None, None]:
    """Get a color gradient from `from_color` to `to_color` with `count` colors.

    :param from_color: Starting color of the gradient.
    :param to_color: Ending color of the gradient.
    :param count: Number of colors in the gradient.
    :return: Generator of colors in the gradient.
    """
    from_color = Color(from_color)
    to_color = Color(to_color)
    yield from (color.hex for color in from_color.range_to(to_color, count))


def get_colormap(from_color: str, to_color: str, count: int, name: str = "my_cmap") -> matplotlib.colors.ListedColormap:
    """Get a colormap from `from_color` to `to_color` with `count` colors.

    :param from_color: Starting color of the colormap.
    :param to_color: Ending color of the colormap.
    :param count: Number of colors in the colormap.
    :return: A matplotlib colormap.
    """
    colors = list(get_color_gradient(from_color, to_color, count))

    return matplotlib.colors.ListedColormap(colors, name=name)


def plot_colored_line_by_param(
    df,
    x_col="Vgs",
    y_col="Ids",
    color_col="Vds",
    cmap=None,
    norm=None,  # <- added norm parameter
    figsize=(8, 6),
    linewidth=3,
    xlabel=None,
    ylabel=None,
    colorbar_label=None,
):
    """Plot a line colored by a parameter from a DataFrame.

    :param df: DataFrame containing the data.
    :param x_col: Column name for x-axis.
    :param y_col: Column name for y-axis.
    :param color_col: Column name for coloring the line.
    :param cmap: Matplotlib colormap or None. If None, uses viridis.
    :param norm: A Normalize or LogNorm instance for color scaling.
    :param figsize: Figure size (width, height).
    :param linewidth: Width of the line.
    :param xlabel: Label for x-axis.
    :param ylabel: Label for y-axis.
    :param colorbar_label: Label for the colorbar.

    :return: Tuple containing (fig, ax) - the figure and axes objects.
    """
    x = df[x_col].values
    y = df[y_col].values
    c = df[color_col].values

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    fig, ax = plt.subplots(figsize=figsize)

    lc = matplotlib.collections.LineCollection(
        segments,
        cmap=cmap or "viridis",
        norm=norm or plt.Normalize(c.min(), c.max()),  # <- use passed norm if given
    )
    lc.set_array(c[:-1])  # Color values for each segment
    lc.set_linewidth(linewidth)

    ax.add_collection(lc)
    ax.autoscale_view()
    ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))

    ax.set_xlabel(xlabel or x_col)
    ax.set_ylabel(ylabel or y_col)

    cbar = fig.colorbar(lc, ax=ax)
    cbar.set_label(colorbar_label or color_col)

    return fig, ax


def plot_in_folder(
    path: str,
    ignore: tuple = (),
    labels: list[str] | None = None,
    *,
    new_figure: bool = True,
    alpha: float = 0.5,
    linestyle: str = "-",
) -> None:
    """Plot data files in a folder with a gradient color scheme.

    This function reads all data files in the specified folder, applies a color gradient
    from `from_color` to `to_color`, and plots the data using the appropriate handler
    for each file. Files specified in the `ignore` tuple are skipped.
    :param path: Path to the folder containing data files.
    :param from_color: Starting color of the gradient.
    :param to_color: Ending color of the gradient.
    :param ignore: Tuple of file indexes to ignore.
    """
    if new_figure:
        fig, ax = plt.subplots()
    paths = list(get_files_in_folder(path, ignore))

    for datafile_path, label in zip(
        get_files_in_folder(path, ignore),
        labels,
        strict=False,
    ):
        ds = Dataset(datafile_path)
        ds.handler.plot(alpha=alpha, label=label, linestyle=linestyle)
    logging.info("Plotted %d IV curves from %s", len(paths), path)


def label_lines(
    xpos: float,
    ypos: float,
    indexes: list[int] | None = None,
    color: str = "auto",
) -> None:
    """Label lines on a plot at a specified x position.

    :param indexes: List of line indexes to label.
    :param xpos: X position to place the labels.
    :param color: Color of the labels.
    """
    if indexes is None:
        indexes = range(len(plt.gca().get_lines()))
    lines = plt.gca().get_lines()
    xvals = [xpos] * len(indexes)
    lines = [lines[i] for i in indexes]
    labelLines(lines, xvals=xvals, fontsize=10, align=True, color=color)
    plt.text(xpos / 15 * 9, ypos, "Gate voltage, V", fontsize=10, color=color)


def color_lines(from_color: str, to_color: str, sort_order_point: float = 0.1) -> None:
    """Color lines on a plot with a gradient color scheme.

    :param from_color: Starting color of the gradient.
    :param to_color: Ending color of the gradient.
    :param sort_order_point: X position to sort the lines by their Y value.
    """
    lines = plt.gca().get_lines()
    lines_sorted = sorted(
        lines,
        key=lambda line: line.get_ydata()[np.argmin(np.abs(line.get_xdata() - sort_order_point))],
    )
    colors = get_color_gradient(from_color, to_color, len(lines))
    for line, color in zip(lines_sorted, colors, strict=True):
        line.set_color(color)


def plot_input_curves(
    path: Path | str,
    drain_voltages: list[float],
    v_gate: np.ndarray,
    ignore: tuple = (),
) -> None:
    """Plot input curves for a given set of drain voltages."""
    files = list(
        get_files_in_folder(path, ignore=ignore),
    )
    fig, ax = plt.subplots()
    data = {drain_voltage: np.zeros(len(files)) for drain_voltage in drain_voltages}
    for i, datafile in enumerate(files):
        handler = Dataset(datafile).handler
        for drain_voltage in drain_voltages:
            data[drain_voltage][i] = handler.get_current_at_voltage(drain_voltage)
    for drain_voltage, current in data.items():
        plt.plot(v_gate, current, "o-", label=f"{drain_voltage * 1000:.0f} mV")

    plt.legend(title=r"Drain-source voltage")
    plt.xlabel("Gate voltage, V")
    plt.ylabel("Drain-source current, I")
    plt.yscale("log")


def plot_threshold_curve(
    path: Path | str,
    v_gate: np.ndarray,
    ignore: tuple = (),
    cut: int = 10,
) -> None:
    """Plot threshold curve for a given set of gate voltages."""
    files = list(
        get_files_in_folder(path, ignore=ignore),
    )
    fig, ax = plt.subplots()
    data = np.zeros(len(files))
    for i, datafile in enumerate(files):
        handler = Dataset(datafile).handler
        data[i] = handler.get_voltage_with_lowest_current()
    plt.plot(v_gate[:cut], data[:cut], "o-")
    plt.xlabel("Gate voltage, V")
    plt.ylabel("Drain-source current, I")
    plt.title("Threshold curve")


def characterize_transistor(
    path: Path | str,
    v_gate: np.ndarray,
    files_to_ignore: tuple = (),
    curves_with_label: tuple = (),
    drain_voltages: tuple | None = None,
    label_position: float = 0.15,
    title_position: float = 1e-3,
) -> None:
    """Characterize a transistor using the given gate voltages."""
    plot_in_folder(path, ignore=files_to_ignore, labels=v_gate)
    plt.title("")
    label_lines(
        indexes=curves_with_label,
        xpos=label_position,
        color="black",
        ypos=title_position,
    )
    color_lines(
        "Blueviolet",
        "Yellow",
    )

    if not drain_voltages:
        datafile = list(get_files_in_folder(path, ignore=files_to_ignore))[-1]
        handler = Dataset(datafile).handler
        drain_voltages = np.arange(handler.first_bias, handler.second_bias, 0.1)
    plot_input_curves(
        path=path,
        drain_voltages=drain_voltages,
        v_gate=v_gate,
        ignore=files_to_ignore,
    )

    plot_threshold_curve(path, v_gate, ignore=files_to_ignore)


def calculate_current_difference(voltages, currents):
    """
    Calculate the current difference between forward and reverse sweeps for a specific voltage.

    Parameters:
    ds (DataFrame): The dataset containing Ids and Vgs values.
    voltage (float): The Vg_limit_second value to filter the dataset.

    Returns:
    tuple: (bias_forward, delta_I) - The bias values and current differences.
    """
    mask = np.diff(voltages)
    # Pad so mask has same length as voltages
    mask_dec = np.insert(mask < 0, 0, False)  # True whenever that point is followed by a decrease
    mask_inc = np.insert(mask > 0, 0, False)  # True whenever that point is followed by an increase

    # Pick out forward and reverse branches, considering all voltages
    b_fwd = np.concatenate(
        [
            voltages[mask_dec & (voltages <= 0)],  # negative forward
            voltages[mask_inc & (voltages >= 0)],  # positive forward
        ]
    )
    I_fwd = np.concatenate(
        [
            currents[mask_dec & (voltages <= 0)],  # negative forward
            currents[mask_inc & (voltages >= 0)],  # positive forward
        ]
    )

    b_rev = np.concatenate(
        [
            voltages[mask_inc & (voltages <= 0)],  # negative reverse
            voltages[mask_dec & (voltages >= 0)],  # positive reverse
        ]
    )
    I_rev = np.concatenate(
        [
            currents[mask_inc & (voltages <= 0)],  # negative reverse
            currents[mask_dec & (voltages >= 0)],  # positive reverse
        ]
    )

    # Sort by bias voltage to ensure correct interpolation
    sort_idx_fwd = np.argsort(b_fwd)
    b_fwd = b_fwd[sort_idx_fwd]
    I_fwd = I_fwd[sort_idx_fwd]

    sort_idx_rev = np.argsort(b_rev)
    b_rev = b_rev[sort_idx_rev]
    I_rev = I_rev[sort_idx_rev]

    # Interpolate reverse sweep to forward sweep bias values
    interp = interp1d(b_rev, I_rev, bounds_error=False, fill_value=np.nan)
    delta_I = I_fwd - interp(b_fwd)

    return b_fwd, delta_I


def get_memory_window(voltages, currents, target_current=0.00005, tolerance=0.05, print_voltages=True):
    idxs = np.argsort(np.abs(currents - target_current))[:2]
    closest_currents = currents.iloc[idxs]
    if abs(closest_currents.iloc[1] - target_current) > tolerance * target_current:
        logging.warning(
            "Current %s not found in data. Closest is %s",
            target_current,
            closest_currents.iloc[0],
        )
        return None
    closest_voltages = voltages.iloc[idxs]
    if print_voltages:
        print("Closest voltages:", closest_voltages.values)
    return np.abs(np.diff(closest_voltages))[0]
