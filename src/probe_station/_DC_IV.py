"""Internal module containing the `DC_IV` class for handling direct current IV data.

The class is designed to be used with the `Dataset` class from the `dataset` module to
parse, analyze, and visualize data from DC IV experiments.
"""  # noqa: N999

from collections.abc import Sequence

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.interpolate import interp1d

from .analysis.common import find_x_at_min_y, get_y_at_x


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
        self.dfs = self._split_data(self.data)

    def _init_metadata(self) -> None:
        """Help to initialize class members with metadata attributes."""
        self.measurement = self.metadata.get("Measurement Number")
        self.measurement_id = self.metadata.get("Measurement ID")
        self.series_id = self.metadata.get("SeriesID")
        self.mode = self.metadata.get("MeasureMode")
        self.first_bias = self.metadata.get("Bias1")
        self.second_bias = self.metadata.get("Bias2")
        self.step = self.metadata.get("Step")
        self.pos_compliance = self.metadata.get("Positive compliance")
        self.neg_compliance = self.metadata.get("Negative compliance")
        self.steps = self.metadata.get("RealMeasuredPoints")

    def _split_data(self, df):
        """Split the IV data into four segments corresponding to each sweep leg.

        The four segments are:

        1. 0 → stop1 (first forward sweep)
        2. stop1 → 0 (first reverse sweep)
        3. 0 → stop2 (second forward sweep)
        4. stop2 → 0 (second reverse sweep)

        :param df: Full IV DataFrame.
        :return: List of four DataFrames.
        """
        df_first_sweep = df[: len(df) // 2]
        df_second_sweep = df[len(df) // 2 :]

        df_0_to_stop1_sweep = df_first_sweep[: len(df_first_sweep) // 2]
        df_stop1_to_zero1_sweep = df_first_sweep[len(df_first_sweep) // 2 :]
        df_zero2_to_stop2_sweep = df_second_sweep[: len(df_second_sweep) // 2]
        df_stop2_to_zero3_sweep = df_second_sweep[len(df_second_sweep) // 2 :]

        return [
            df_0_to_stop1_sweep,
            df_stop1_to_zero1_sweep,
            df_zero2_to_stop2_sweep,
            df_stop2_to_zero3_sweep,
        ]

    def plot(
        self,
        color: str | None = None,
        alpha: float = 1.0,
        label: float | str | None = None,
        linestyle: str = "-",
        xlabel: str = "Voltage, V",
        ylabel: str = "Current, A",
        ax: plt.Axes | None = None,
    ) -> None:
        """Plot the DC IV data.

        :param color: The color of the plot line.
        :param alpha: The transparency level of the plot line.
        """
        if np.issubdtype(type(label), np.floating):
            label = f"{label:.2f}"
        if ax is None:
            ax = plt.gca()
        ax.plot(
            self.data["Bias"],
            np.abs(self.data["Current"]),
            color=color,
            alpha=alpha,
            label=label,
            linestyle=linestyle,
        )
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        plt.title(f"DC IV Measurement {self.measurement}")
        plt.yscale("log")

    def get_current_at_voltage(self, voltage: float, tolerance: float = 5e-2) -> float:
        """Return the current at the specified voltage.

        :param voltage: The voltage at which to get the current.
        :param tolerance: Maximum allowed difference between target and actual voltage.
        :return: The current at the specified voltage.
        """
        midpoint = len(self.data) // 2
        first_branch = self.data[:midpoint].reset_index(drop=True)
        second_branch = self.data[midpoint:].reset_index(drop=True)
        first_current = get_y_at_x(first_branch["Bias"], first_branch["Current"], voltage, tolerance)
        second_current = get_y_at_x(second_branch["Bias"], second_branch["Current"], voltage, tolerance)
        return first_current, second_current

    def get_voltage_with_lowest_current(self) -> float:
        """Return the voltage at which the current is the lowest.

        :return: The voltage at which the current is the lowest.
        """
        return find_x_at_min_y(self.data["Bias"], self.data["Current"])

    def measure_resistance_ratio(
        self,
        voltage: float,
        tolerance: float = 5e-2,
    ) -> float:
        """Measure the resistance ratio at the specified voltage.

        :param voltage: The voltage at which to measure the resistance ratio.
        :return: The resistance ratio at the specified voltage.
        """
        voltages = self.data["Bias"]
        current = self.data["Current"]
        indexes = np.where(np.diff(np.sign(voltages - voltage)))[0]
        if len(indexes) == 4:
            index1, index2 = indexes[1:3]
        else:
            index1, index2 = indexes

        voltage1 = voltages.iloc[index1]
        voltage2 = voltages.iloc[index2]

        current1 = current.iloc[index1]
        current2 = current.iloc[index2]
        ratio = np.abs((voltage1 / current1) / (voltage2 / current2))

        return ratio if ratio > 1 else 1 / ratio

    def plot_difference_current(self) -> None:
        """Plot the difference between 2 branches of current."""

        bias = self.data.Bias
        current = self.data.Current

        mask = np.diff(bias)
        # pad so mask has same length as bias
        mask_dec = np.insert(mask < 0, 0, False)  # True whenever that point is followed by a decrease
        mask_inc = np.insert(mask > 0, 0, False)  # True whenever that point is followed by an increase

        # pick out four branches
        b_neg_fwd = bias[mask_dec & (bias <= 0)]
        I_neg_fwd = current[mask_dec & (bias <= 0)]

        b_neg_rev = bias[mask_inc & (bias <= 0)]
        I_neg_rev = current[mask_inc & (bias <= 0)]

        b_pos_fwd = bias[mask_inc & (bias >= 0)]
        I_pos_fwd = current[mask_inc & (bias >= 0)]

        b_pos_rev = bias[mask_dec & (bias >= 0)]
        I_pos_rev = current[mask_dec & (bias >= 0)]

        # interpolate and get delta_I for neg and pos
        interp_neg = interp1d(b_neg_rev, I_neg_rev, bounds_error=False, fill_value=np.nan)
        delta_I_neg = I_neg_fwd - interp_neg(b_neg_fwd)

        interp_pos = interp1d(b_pos_rev, I_pos_rev, bounds_error=False, fill_value=np.nan)
        delta_I_pos = I_pos_fwd - interp_pos(b_pos_fwd)

        plt.plot(b_neg_fwd, delta_I_neg, "s-", label="ΔI (negative branch)")
        # plt.vlines(x=-2.8, ymin=-4e-10, ymax=6e-10)
        plt.plot(b_pos_fwd, delta_I_pos, "o-", label="ΔI (positive branch)")
        plt.axvline(0, color="gray", lw=0.5)
        plt.xlabel("Bias (V)")
        plt.ylabel("Current difference ΔI (A)")
        plt.legend()
        plt.tight_layout()
