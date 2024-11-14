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
        key=lambda line: line.get_ydata()[
            np.argmin(np.abs(line.get_xdata() - sort_order_point))
        ],
    )
    colors = get_color_gradient(from_color, to_color, len(lines))
    for line, color in zip(lines_sorted, colors, strict=True):
        line.set_color(color)
