"""Module contains utility functions for the probe station project."""

import logging
from collections.abc import Generator
from pathlib import Path

import matplotlib.pyplot as plt
import scienceplots  # noqa: F401

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


def plot_in_folder(
    path: str,
    ignore: tuple = (),
    labels: list[str] | None = None,
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
    fig, ax = plt.subplots()
    paths = list(get_files_in_folder(path, ignore))

    for datafile_path, label in zip(
        get_files_in_folder(path, ignore),
        labels,
        strict=False,
    ):
        ds = Dataset(datafile_path)
        ds.handler.plot(alpha=0.5, label=label)
    logging.info("Plotted %d IV curves from %s", len(paths), path)
