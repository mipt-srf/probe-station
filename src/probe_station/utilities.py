"""Module contains utility functions for the probe station project."""

import logging
from collections.abc import Generator
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import scienceplots  # noqa: F401
from colour import Color
from labellines import labelLines

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


def get_color_gradient(from_color: str, to_color: str, count: int) -> list[str]:
    """Get a color gradient from `from_color` to `to_color` with `count` colors.

    :param from_color: Starting color of the gradient.
    :param to_color: Ending color of the gradient.
    :param count: Number of colors in the gradient.
    :return: List of colors in the gradient.
    """
    from_color = Color(from_color)
    to_color = Color(to_color)
    yield from (color.hex for color in from_color.range_to(to_color, count))


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
