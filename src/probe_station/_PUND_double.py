"""Internal module containing the `PUND_double` class for handling PUND data.

The class is designed to be used with the `Dataset` class from the `dataset` module to parse,
analyze, and visualize data from PUND Double experiments.
"""  # noqa: N999

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pandas as pd


class PUND_double:  # noqa: N801
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
        :param pad_size_um: The pad size in um.
            Used for correct polarization calculation.
        """
        self.pad_size_um = pad_size_um
        self.charge_df = dataframes[0]
        self.metadata = metadata
        self._init_metadata()

    def _init_metadata(self) -> None:
        """Help to initialize class members with metadata attributes."""
        self.measurement = self.metadata["Measurement Number"]
        self.measurement_id = self.metadata["Measurement ID"]
        self.first_bias = self.metadata["Voltage High"]
        self.second_bias = self.metadata["Voltage Low"]
        self.repetitions = self.metadata["Repetitions"]
        self.pulse_width = self.metadata["Pulse Width"]
        self.pulse_separation = self.metadata["Pulse Separation"]
        self.slope_time = self.metadata["Trails"]

    def plot(self, filtering_window=1) -> None:
        """Plot the polarization vs cycles."""
        fig, ax = plt.subplots(figsize=(10, 5))

        polarization_charge = (
            self.charge_df["P"] - self.charge_df["U"] - self.charge_df["N"] + self.charge_df["D"]
        ) / 2
        polarization = polarization_charge / self.pad_size_um**2 * 1e14

        polarization = np.abs(polarization.rolling(window=filtering_window, center=True).mean())  # filter noise

        ax.plot(polarization)
        ax.set_title(f"PUND Double Measurement {self.measurement}")
        plt.xlabel("Cycles")
        plt.ylabel("Polarization, uC/cm^2")
        plt.ylim(np.min(polarization) * 0.5, np.max(polarization) * 1.05)

    def plot_charges(self, filtering_window=1) -> None:
        """Plot P, U, N, D charges vs cycles."""
        fig, ax = plt.subplots(figsize=(10, 5))

        columns = ["P", "U", "N", "D"]
        for column in columns:
            ax.plot(self.charge_df[column].rolling(window=filtering_window, center=True).mean(), label=column)
        ax.legend()

        ax.set_title(f"PUND Double Measurement {self.measurement}")
        plt.xlabel("Cycles")
        plt.ylabel("Polarization, uC/cm^2")
