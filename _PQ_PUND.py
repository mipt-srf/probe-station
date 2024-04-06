"""
Internal module containing the `PQ_PUND` class for handling quasistatic
IV data. The class is designed to be used with the `Dataset` class from
the `dataset` module to parse, analyze, and visualize data from DC IV
experiments.
"""

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from numpy.typing import NDArray


class PQ_PUND:
    def __init__(
        self, metadata: dict, dataframes: Sequence[pd.DataFrame], big_pad: bool = False
    ) -> None:
        """Initializes the class instance with the given metadata and
        dataframes extracted using `Dataset._parse_datafile()`.

        :param metadata: A dictionary containing metadata information.
        :param dataframes: A sequence of pandas DataFrames.
        :param big_pad: ``True`` if the pad is 100um^2, ``False`` if 25um^2.
            Used for correct polarization calculation.
        """
        self.big_pad = big_pad
        self.current_df = dataframes[0]
        self.leakage_df = dataframes[1]
        self.qv_df = dataframes[2]
        self.metadata = metadata
        self._init_metadata()
        self.current_df["DiffCurrent"] = (
            self.current_df["CurrentP"]
            - self.current_df["CurrentC"]
            + self.leakage_df["CurrentP"]
            - self.leakage_df["CurrentC"]
        )

    def _init_metadata(self) -> None:
        """Helper function that initializes class members with metadata
        attributes.
        """
        self.measurement = self.metadata["Measurement Number"]
        self.measurement_id = self.metadata["Measurement ID"]
        self.first_bias = self.metadata["First Bias"]
        self.second_bias = self.metadata["Second Bias"]
        self.steps = self.metadata["Steps"]
        self.repetitions = self.metadata["Repetition"]
        self.rump_time = self.metadata["Rump time"]
        self.rump_integration_time = self.metadata["Rump Interg time"]
        self.wait_time = self.metadata["Wait Time"]
        self.wait_integration_time = self.metadata["Wait Integr Time"]
        self.steps_per_cycle = 2 * (self.steps - 1)

    def get_cycle(self, cycle: int, plot: bool = False) -> pd.DataFrame:
        """Get a specific cycle data from the dataset.

        :param cycle: The cycle number for which to retrieve data.
        :param plot: Whether to plot the cycle data.

        :return: `Dataframe` containing the specific cycle data.
        """
        df_cycle = self.current_df[
            cycle * self.steps_per_cycle : (cycle + 1) * self.steps_per_cycle
        ]
        if plot:
            df_cycle.plot("Voltages", y=["DiffCurrent"])  # type: ignore
        return df_cycle

    def get_half_cycle(
        self,
        cycle: int,
        positive: bool = True,
        plot: bool = False,
    ) -> pd.DataFrame:
        """Get a specific half-cycle data from the dataset.

        :param cycle: The cycle number for which to retrieve data.
        :param positive: Flag to indicate if the part with positive
            current should be extracted.
        :param plot: Flag to indicate whether to plot the data.

        :return: `DataFrame` containing data for specified half-cycle.
        """
        if self.first_bias > self.second_bias:  # consider direction of bias change
            positive = not positive
        df1 = self.get_data_from_range(
            cycle, points_number=self.steps_per_cycle // 2, positive=positive
        )

        if plot:
            df1.plot(
                "Voltages",
                y=["DiffCurrent"],
                xlim=(
                    self.current_df["Voltages"].min() * 1.05,
                    self.current_df["Voltages"].max() * 1.05,
                ),
                ylim=(
                    self.current_df["DiffCurrent"].min() * 1.05,
                    self.current_df["DiffCurrent"].max() * 1.05,
                ),
            )  # type: ignore
        return df1

    def get_data_from_range(
        self,
        cycle: int,
        positive: bool = True,
        start: int = 0,
        points_number: int = 50,
        plot_cycle: bool = False,
    ) -> pd.DataFrame:
        """Retrieves data from a specified steps range.

        :param cycle: The cycle number to retrieve data from.
        :param positive: Whether to retrieve data from the half cycle
            with positive current.
        :param start: The starting index of the data range within
            the half-cycle.
        :param points_number: The number of points to retrieve from the
            data range.
        :param plot_cycle: Whether to plot the cycle that cointans the
            data range.

        :return: The retrieved data from the specified range.
        """
        steps_per_cycle = 2 * (self.steps - 1)
        shift_half_cycle = positive * 0.5
        left = int((cycle + shift_half_cycle) * steps_per_cycle) + start
        right = left + points_number
        df1 = self.current_df[left:right]
        if plot_cycle:
            _ = self.get_cycle(cycle, plot=plot_cycle)
            self.plot_point_on_data(left)
            self.plot_point_on_data(right)
        return df1

    def plot_iv_cycled(
        self,
        sample: str = "",
        ylim: tuple[float, float] | None = None,
    ) -> None:
        """Plot the cycled PQ static curve.

        :param sample: The sample name for labeling the plot title.
        :param ylim: The y-axis limits for the plot.
        """
        transparencies = np.logspace(-0.4, -0.01, self.repetitions)
        for i, alpha in enumerate(transparencies):
            df_cycle = self.get_cycle(i, plot=False)
            label = None
            if i == 0 or i == self.repetitions - 1:
                label = f"cycle #{i+1}"
            plt.plot(
                df_cycle["Voltages"],
                df_cycle["DiffCurrent"],
                alpha=alpha,
                color="b",
                label=label,
            )
            if ylim:
                plt.ylim(ylim)
        plt.xlabel("Voltage, V")
        plt.ylabel("Current, A")
        plt.title(f"I-V curve {sample}")
        plt.legend(loc="upper left")

    def plot_point_on_data(
        self, point: int, xdata: str = "Voltages", ydata: str = "DiffCurrent"
    ) -> None:
        """Plot a point on the data graph.

        :param point: Index of the point to plot.
        :param xdata: Name of the x-axis data column.
        :param ydata: Name of the y-axis data column.
        """
        plt.plot(
            self.current_df[xdata].iloc[point], self.current_df[ydata].iloc[point], "x"
        )

    def get_polarization(
        self,
        cycle: int,
        positive: bool = True,
        plot_cycle: bool = False,
    ) -> float:
        """Calculate the polarization value for a given cycle.

        :param cycle: The cycle number for which to calculate the
            polarization.
        :param positive: Whether to calculate the positive or negative
            polarization.
        :param plot_cycle: Whether to plot the cycle data.

        :return: The calculated polarization value.
        """
        df_cycle = self.get_half_cycle(cycle, positive=positive, plot=plot_cycle)
        time_step = self.wait_time + self.rump_time
        times = np.array([time_step * i for i in range(df_cycle["Voltages"].size)])
        charge = scipy.integrate.simpson(y=df_cycle["DiffCurrent"], x=times)
        area = (25e-4) ** 2
        if self.big_pad:
            area *= 16
        polarization = charge / area * 1e6
        return polarization

    def get_polarizations(
        self,
        positive: bool = True,
        plot_result: bool = True,
        plot_cycles: bool = False,
    ) -> NDArray[np.float64]:
        """Calculate polarization for each cycle, and optionally plot
        the results (wake-up curve for polarization).

        :param positive: Whether to calculate positive or negative
            polarizations.
        :param plot_result: Whether to plot the results.
        :param plot_cycles: Whether to plot individual cycles. Used to
            check if data for polarization calculation is correct.

        :return: Array of polarizations.
        """
        pols = []
        for i in range(self.repetitions):
            polarization = self.get_polarization(
                cycle=i, positive=positive, plot_cycle=plot_cycles
            )
            pols.append(polarization)
        polarizations = np.array(pols)
        if not positive:
            polarizations *= -1

        if plot_result:
            sign = "+" if positive else "-"
            color = "r" if positive else "b"
            plt.plot(polarizations, ".-", label=rf"$P_{sign}$", color=color)
            plt.xlabel("Cycles")
            plt.ylabel(r"Polarization, $\mu C$/cm$^2$")
            plt.legend(loc="lower right")
            plt.gca().set_ylim(0, polarizations.max() * 1.05)
        return polarizations

    def plot_qv(
        self,
        cycle: int = -1,
        centered: bool = True,
        show_cycle: bool = False,
        sample: str = "",
    ) -> None:
        """Generate a plot of the polarization versus voltage for a
        specific cycle (last by default).

        :param cycle: The cycle number to plot. ``-1`` means the last cycle.
        :param centered: If ``True``, center the polarization values around zero.
        :param show_cycle: If ``True``, display the cycle number in the plot.
        :param sample: Sample name to display in the plot label.
        """
        if cycle == -1:
            cycle = self.repetitions - 1
        df_cycle = self.get_cycle(cycle)
        time_step = self.wait_time + self.rump_time
        times = np.array([time_step * i for i in range(df_cycle["Voltages"].size)])

        voltages = df_cycle["Voltages"]
        curr = df_cycle["DiffCurrent"]
        area = (25e-4) ** 2
        if self.big_pad:
            area *= 16
        polarizations = (
            scipy.integrate.cumulative_trapezoid(curr, times, initial=0) / area * 1e6
        )
        if centered:
            polarizations -= polarizations.mean()

        label = f"cycle #{cycle}" if show_cycle else None
        label = label + (sample) if label else sample
        plt.plot(voltages, polarizations, label=label)
        plt.xlabel("Voltage, V")
        plt.ylabel(r"Polarization, $\mu C$/cm$^2$")
        if show_cycle:
            plt.legend(loc="lower right")
