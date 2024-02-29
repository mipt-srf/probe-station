from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class PQ_PUND:
    def __init__(self, metadata: dict, dataframes: Sequence[pd.DataFrame]) -> None:
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
            )
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

    def plot_wakeup(
        self,
        output_path: Path | str = ".",
        sample: str = "",
        ylim: tuple[float, float] | None = None,
    ):
        repetitions = self.metadata["Repetition"]

        transparencies = np.logspace(-0.4, -0.01, repetitions)
        for i, alpha in enumerate(transparencies):
            df_cycle = self.get_cycle(i, plot=False)
            label = None
            if i == 0 or i == repetitions - 1:
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
