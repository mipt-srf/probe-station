"""Internal module containing the `CV` class for handling capacitance-voltage (CV) data.

The class is designed to be used with the `Dataset` class from the `dataset` module to
parse, analyze, and visualize data from CV experiments.
"""  # noqa: N999

from collections.abc import Sequence

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt


class CV:
    def __init__(
        self,
        metadata: dict,
        dataframes: Sequence[pd.DataFrame],
        *,
        pad_size_um: float = 0.0,
    ) -> None:
        """Initialize the class instance with the given metadata and dataframes`.

        Given metadata and dataframes are extracted using `Dataset._parse_datafile()`

        :param metadata: A dictionary containing metadata information.
        :param dataframes: A sequence of pandas DataFrames.
        :param pad_size_um: The size of the pad in micrometers.
        """
        self.pad_size_um = pad_size_um
        self.data = dataframes[0]
        self.metadata = metadata
        self._init_metadata()

    def _init_metadata(self) -> None:
        """Help to initialize class members with metadata attributes."""
        self.measurement = self.metadata.get("Measurement Number")
        self.measurement_id = self.metadata.get("Measurement ID")
        self.series_id = self.metadata.get("SeriesID")
        self.mode = self.metadata.get("MeasureMode")
        self.first_bias = self.metadata.get("Start")
        self.second_bias = self.metadata.get("Stop")
        self.step = self.metadata.get("Step")
        self.sweep_mode = self.metadata.get("Sweep mode")
        self.frequency = self.metadata.get("Frequency")
        self.steps = self.metadata.get("RealMeasuredPoints")

    def calculate_capacitance(self, *, force_series: bool = False, force_parallel: bool = False) -> None:
        """Calculate the capacitance from the CV data according to Cs - Rs scheme."""
        resistance = self.data["Resistance"]
        reactance = self.data["Reactance"]
        capacitance_series = -1 / (2 * np.pi * self.frequency * reactance)
        if not force_series and self.check_resistance() or force_parallel:
            return capacitance_series / (1 + (resistance / reactance) ** 2)
        return capacitance_series

    def check_resistance(self) -> None:
        resistance = self.data["Resistance"]
        return all(resistance > 1)

    def plot(
        self,
        color: str | None = None,
        alpha: float = 1.0,
        label: float | str | None = None,
        linestyle: str = "-",
    ) -> None:
        """Plot the CV data.

        :param color: The color of the plot line.
        :param alpha: The transparency level of the plot line.
        """
        plt.plot(
            self.data["Voltage"],
            np.abs(self.calculate_capacitance()),
            label=label,
            color=color,
        )
        plt.yscale("log")
        plt.ylabel("Capacitance, F")
        plt.xlabel("Voltage, V")

    def plot_epsilon(
        self,
        area: float,
        thickness: float,
        color: str | None = None,
        alpha: float = 1.0,
        label: float | str | None = None,
        linestyle: str = "-",
    ) -> None:
        """Plot the CV data.

        :param color: The color of the plot line.
        :param alpha: The transparency level of the plot line.
        """
        capacitance = np.abs(self.calculate_capacitance())
        epsilon0 = 8.854e-12
        epsilon = capacitance / epsilon0 / area * thickness
        plt.plot(self.data["Voltage"], epsilon, label=label, color=color)
        plt.ylabel("Dielectric constant")
        plt.xlabel("Voltage, V")
