"""Internal module containing the `PQ_PUND` class for handling quasistatic IV data.

The class is designed to be used with the `Dataset` class from
the `dataset` module to parse, analyze, and visualize data from DC IV
experiments.
"""  # noqa: N999

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.optimize import curve_fit

from probe_station.common import get_coercive_voltages, plot_vlines

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray


class PQ_PUND:  # noqa: N801
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
        self.transition_current_df = dataframes[0].rename(
            columns={"CurrentP": "Pos/Neg Current", "CurrentC": "Up/Down Current"}
        )
        self.plateau_current_df = dataframes[1].rename(
            columns={"CurrentP": "Pos/Neg Current", "CurrentC": "Up/Down Current"}
        )
        self.qv_df = dataframes[2]
        self.metadata = metadata
        self._init_metadata()

        self.transition_current_df["Polarization Current"] = (
            self.transition_current_df["Pos/Neg Current"] - self.transition_current_df["Up/Down Current"]
        )
        self.plateau_current_df["Polarization Current"] = (
            self.plateau_current_df["Pos/Neg Current"] - self.plateau_current_df["Up/Down Current"]
        )
        self.polarization_current_df = pd.DataFrame(
            {
                "Voltages": self.transition_current_df["Voltages"],
                "Polarization Current": self.transition_current_df["Polarization Current"]
                + self.plateau_current_df["Polarization Current"],
            }
        )

    def _init_metadata(self) -> None:
        """Help to initialize class members with metadata attributes."""
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

    def get_cycle(self, cycle: int, *, plot: bool = False) -> pd.DataFrame:
        """Get a specific cycle data from the dataset.

        :param cycle: The cycle number for which to retrieve data.
        :param plot: Whether to plot the cycle data.

        :return: `Dataframe` containing the specific cycle data.
        """
        df_cycle = self.polarization_current_df[cycle * self.steps_per_cycle : (cycle + 1) * self.steps_per_cycle]
        if plot:
            df_cycle.plot("Voltages", y=["Polarization Current"])
        return df_cycle

    def get_half_cycle(
        self,
        cycle: int,
        *,
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
            cycle,
            points_number=self.steps_per_cycle // 2,
            positive=positive,
        )

        if plot:
            df1.plot(
                "Voltages",
                y=["Polarization Current"],
                xlim=(
                    self.polarization_current_df["Voltages"].min() * 1.05,
                    self.polarization_current_df["Voltages"].max() * 1.05,
                ),
                ylim=(
                    self.polarization_current_df["Polarization Current"].min() * 1.05,
                    self.polarization_current_df["Polarization Current"].max() * 1.05,
                ),
            )
        return df1

    def get_data_from_range(
        self,
        cycle: int,
        *,
        positive: bool = True,
        start: int = 0,
        points_number: int = 50,
        plot_cycle: bool = False,
    ) -> pd.DataFrame:
        """Retrieve data from a specified steps range.

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
        df1 = self.polarization_current_df[left:right]
        if plot_cycle:
            _ = self.get_cycle(cycle, plot=plot_cycle)
            self.plot_point_on_data(left)
            self.plot_point_on_data(right)
        return df1

    def fit_leakage(self, from_positive, from_negative, plot=True) -> None:
        """Fit the leakage current data."""

        def leakage_current_model(V, I0, a):
            return I0 * np.exp(a * V)

        # def leakage_current_model(V, I0, b):
        #     return I0 * V**2 * np.exp(b / V)

        voltages = self.polarization_current_df["Voltages"]
        currents = self.polarization_current_df["Polarization Current"]

        mask_positive = voltages > from_positive
        fit_voltages_positive = voltages[mask_positive]
        fit_currents_positive = currents[mask_positive]

        mask_negative = voltages < from_negative
        fit_voltages_negative = voltages[mask_negative]
        fit_currents_negative = currents[mask_negative]

        popt_positive, pcov_positive = curve_fit(
            leakage_current_model,
            fit_voltages_positive,
            np.abs(fit_currents_positive),
            p0=[1e-6, 1],
        )

        popt_negative, pcov_negative = curve_fit(
            leakage_current_model,
            fit_voltages_negative,
            fit_currents_negative,
            p0=[-1e-6, 1],
        )

        leakage_current_positive = leakage_current_model(
            voltages,
            *popt_positive,
        )
        leakage_current_negative = leakage_current_model(
            voltages,
            *popt_negative,
        )
        leakage_current = leakage_current_positive + leakage_current_negative

        if plot:
            fig, axs = plt.subplots(2, 1)

            axs[0].plot(
                voltages,
                currents,
                label="Experimental Data",
            )
            axs[0].plot(
                voltages,
                leakage_current,
                label="Leakage Current Fit",
            )
            axs[0].legend()

            axs[1].plot(voltages, currents - leakage_current)

            fig.suptitle("Leakage Current Fitting")
            fig.supxlabel("Voltage, V")
            fig.supylabel("Current, A")
            plt.show()
        return leakage_current

    def remove_leakage_current(self, from_positive, from_negative, plot=True) -> None:
        """Remove leakage current from the data."""

        leakage_current = self.fit_leakage(from_positive, from_negative, plot=plot)
        self.polarization_current_df["Polarization Current"] -= leakage_current

    def substract_wait_current(self, from_positive=None) -> None:
        """Subtract the wait current from the data."""
        voltage = self.plateau_current_df["Voltages"]
        voltage_filter = voltage > from_positive
        self.polarization_current_df.loc[voltage_filter, "Polarization Current"] -= self.plateau_current_df["CurrentC"][
            voltage_filter
        ]

    def shift_current(self, shift: float) -> None:
        """Shift the current data by a given value.

        :param shift: The value by which to shift the current data.
        """
        self.polarization_current_df["Polarization Current"] += shift

    def plot(self):
        self.plot_iv_cycled()

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
                label = f"cycle #{i + 1}"
            plt.plot(
                df_cycle["Voltages"],
                df_cycle["Polarization Current"],
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
        self,
        point: int,
        xdata: str = "Voltages",
        ydata: str = "Polarization Current",
    ) -> None:
        """Plot a point on the data graph.

        :param point: Index of the point to plot.
        :param xdata: Name of the x-axis data column.
        :param ydata: Name of the y-axis data column.
        """
        plt.plot(
            self.transition_current_df[xdata].iloc[point],
            self.transition_current_df[ydata].iloc[point],
            "x",
        )

    def get_polarization(
        self,
        cycle: int,
        *,
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
        charge = scipy.integrate.simpson(y=df_cycle["Polarization Current"], x=times)
        area = (self.pad_size_um * 1e-4) ** 2
        return charge / area * 1e6

    def get_polarizations(
        self,
        *,
        positive: bool = True,
        plot_result: bool = True,
        plot_cycles: bool = False,
    ) -> NDArray[np.float64]:
        """Calculate polarization for each cycle, and optionally plot wake-up curve.

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
                cycle=i,
                positive=positive,
                plot_cycle=plot_cycles,
            )
            pols.append(polarization)
        polarizations = np.array(pols, dtype=np.float64)
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

    def get_coercive_voltages(self, cycle: int = -1, plot=False) -> tuple[float, float]:
        """Get positive and negative coercive fields.

        :return: Tuple containing positive and negative coercive fields.
        """
        if cycle == -1:
            cycle = self.repetitions - 1

        df_cycle = self.get_cycle(cycle)
        currents = df_cycle["Polarization Current"]
        voltages = df_cycle["Voltages"]

        negative_coercive_field, positive_coercive_field = get_coercive_voltages(voltages, currents, plot=plot)

        if plot:
            plt.plot(voltages, currents)
            plt.xlabel("Voltage, V")
            plt.ylabel("Current, A")
            plt.title("Detected coercive fields")
            plot_vlines([negative_coercive_field, positive_coercive_field])
            plt.legend()

        return negative_coercive_field, positive_coercive_field

    def plot_pv(
        self,
        cycle: int = -1,
        *,
        centered: bool = True,
        show_cycle: bool = False,
        sample: str = "",
    ) -> None:
        """Generate a plot of the polarization versus voltage for a specific cycle.

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
        curr = df_cycle["Polarization Current"]
        area = (self.pad_size_um * 1e-4) ** 2
        polarizations = scipy.integrate.cumulative_trapezoid(curr, times, initial=0) / area * 1e6
        if centered:
            polarizations -= polarizations.mean()

        label = f"cycle #{cycle}" if show_cycle else None
        label = label + (sample) if label else sample
        plt.plot(voltages, polarizations, label=label)
        plt.xlabel("Voltage, V")
        plt.ylabel(r"Polarization, $\mu C$/cm$^2$")
        plt.title("P-V curve")
        if show_cycle:
            plt.legend(loc="lower right")
