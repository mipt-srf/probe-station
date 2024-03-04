from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy


class PQ_PUND:
    def __init__(
        self, metadata: dict, dataframes: Sequence[pd.DataFrame], big_pad: bool = False
    ) -> None:
        self.big_pad = big_pad
        self.current_df = dataframes[0]
        self.leakage_df = dataframes[1]
        self.qv_df = dataframes[2]
        self.metadata = metadata
        self._init_metadata()
        self.current_df["DiffCurrent"] = (
            self.current_df["CurrentP"]
            - self.current_df["CurrentC"]
            # + self.leakage_df["CurrentP"]
        )

    def _init_metadata(self):
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

    def get_cycle(self, cycle: int, plot: bool = False):
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
    ):
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
    ):
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
        output_path: Path | str = ".",
        sample: str = "",
        ylim: tuple[float, float] | None = None,
    ):
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
        plt.savefig(Path(output_path, sample + " wakeup (pq).png"), bbox_inches="tight")

    def plot_point_on_data(
        self, point: int, xdata: str = "Voltages", ydata: str = "DiffCurrent"
    ):
        plt.plot(
            self.current_df[xdata].iloc[point], self.current_df[ydata].iloc[point], "x"
        )

    def get_polarization(
        self,
        cycle: int,
        positive: bool = True,
        plot_cycle: bool = False,
    ):
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
    ):
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

    def plot_qv(self, cycle: int = -1, centered: bool = True, plot_cycle: bool = False):
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

        plt.plot(
            voltages, polarizations, label=f"cycle #{cycle}" if plot_cycle else None
        )
        plt.xlabel("Voltage, V")
        plt.ylabel(r"Polarization, $\mu C$/cm$^2$")
        if plot_cycle:
            plt.legend(loc="lower right")
