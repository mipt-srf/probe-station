import pandas as pd
from matplotlib import pyplot as plt


def get_cycle(df: pd.DataFrame, metadata: dict, cycle: int, plot: bool = False):
    steps_per_cycle = 2 * (int(metadata["Steps"]) - 1)
    df_cycle = df[cycle * steps_per_cycle : (cycle + 1) * steps_per_cycle]
    if plot:
        df_cycle.plot("Voltages", y=["DiffCurrent"])  # type: ignore
    return df


def get_half_cycle(
    df: pd.DataFrame,
    metadata: dict,
    cycle: int,
    positive: bool = True,
    plot: bool = False,
):
    steps_per_cycle = 2 * (int(metadata["Steps"]) - 1)
    df1 = get_data_from_range(
        df, metadata, cycle, points_number=steps_per_cycle // 2, positive=positive
    )

    if plot:
        df1.plot(
            "Voltages",
            y=["DiffCurrent"],
            xlim=(df["Voltages"].min() * 1.05, df["Voltages"].max() * 1.05),
            ylim=(df["DiffCurrent"].min() * 1.05, df["DiffCurrent"].max() * 1.05),
        )
    return df1


def get_data_from_range(
    df: pd.DataFrame,
    metadata: dict,
    cycle: int,
    positive: bool = True,
    start: int = 0,
    points_number: int = 50,
    plot_cycle: bool = False,
):
    steps_per_cycle = 2 * (int(metadata["Steps"]) - 1)
    shift_half_cycle = positive * 0.5
    left = int((cycle + shift_half_cycle) * steps_per_cycle) + start
    right = left + points_number
    df1 = df[left:right]
    if plot_cycle:
        _ = get_cycle(df, metadata, cycle, plot=plot_cycle)
        plot_point_on_data(df, left)
        plot_point_on_data(df, right)
    return df1


def plot_point_on_data(
    df: pd.DataFrame, point: int, xdata: str = "Voltages", ydata: str = "DiffCurrent"
):
    plt.plot(df[xdata].iloc[point], df[ydata].iloc[point], "x")
