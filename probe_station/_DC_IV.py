"""Internal module containing the `DC_IV` class for handling direct current IV data.

The class is designed to be used with the `Dataset` class from the `dataset` module to
parse, analyze, and visualize data from DC IV experiments.
"""  # noqa: N999

import logging
from collections.abc import Sequence

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt


class DC_IV:  # noqa: N801
    def __init__(
        self,
        metadata: dict,
        dataframes: Sequence[pd.DataFrame],
        *,
        pad_size_um: float = 25.0,
    ) -> None:
        """Initialize the class instance with the given metadata and dataframes.

        Given metadata and dataframes are extracted using `Dataset._parse_datafile()`

        :param metadata: A dictionary containing metadata information.
        :param dataframes: A sequence of pandas DataFrames.
        :param pad_size_um: A float indicating the pad size in um.
        """
        self.pad_size_um = pad_size_um
        self.data = dataframes[0]
        self.metadata = metadata
        self._init_metadata()

    def _init_metadata(self) -> None:
        """Help to initialize class members with metadata attributes."""
        self.measurement = self.metadata["Measurement Number"]
        self.measurement_id = self.metadata["Measurement ID"]
        self.series_id = self.metadata["SeriesID"]
        self.mode = self.metadata["MeasureMode"]
        self.first_bias = self.metadata["Bias1"]
        self.second_bias = self.metadata["Bias2"]
        self.step = self.metadata["Step"]
        self.pos_compliance = self.metadata["Positive compliance"]
        self.neg_compliance = self.metadata["Negative compliance"]
        self.steps = self.metadata["RealMeasuredPoints"]

    def plot(
        self,
        color: str | None = None,
        alpha: float = 1.0,
        label: float | str | None = None,
        linestyle: str = "-",
    ) -> None:
        """Plot the DC IV data.

        :param color: The color of the plot line.
        :param alpha: The transparency level of the plot line.
        """
        if np.issubdtype(type(label), np.floating):
            label = f"{label:.2f}"
        plt.plot(
            self.data["Bias"],
            np.abs(self.data["Current"]),
            color=color,
            alpha=alpha,
            label=label,
            linestyle=linestyle,
        )
        plt.xlabel("Drain-source voltage, V")
        plt.ylabel("Drain current, A")

        plt.title(f"DC IV Measurement {self.measurement}")
        plt.yscale("log")

    def get_current_at_voltage(self, voltage: float, tolerance: float = 5e-2) -> float:
        """Return the current at the specified voltage.

        :param voltage: The voltage at which to get the current.
        :return: The current at the specified voltage.
        """
        idx = np.abs(self.data["Bias"] - voltage).idxmin()
        closest_voltage = self.data["Bias"].iloc[idx]
        if abs(closest_voltage - voltage) > tolerance:
            logging.warning(
                "Voltage %s not found in data. Closest is %s",
                voltage,
                closest_voltage,
            )
        return np.abs(self.data["Current"].iloc[idx])

    def get_voltage_with_lowest_current(self) -> float:
        """Return the voltage at which the current is the lowest.

        :return: The voltage at which the current is the lowest.
        """
        idx = self.data["Current"].abs().idxmin()
        return self.data["Bias"].iloc[idx]
