import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy  # type: ignore

from probe_station.processor import get_half_cycle


def get_polarization(df: pd.DataFrame, metadata: dict, big_pad: bool = False):
    wait_time, rump_time = metadata["Wait Time"], metadata["Rump time"]
    time_step = wait_time + rump_time
    times = np.array([time_step * i for i in range(df["Voltages"].size)])
    charge = scipy.integrate.simpson(y=df["DiffCurrent"], x=times)
    area = (25e-4) ** 2
    if big_pad:
        area *= 16
    polarization = charge / area * 1e6
    return polarization


def get_default_wakeup(
    df: pd.DataFrame,
    metadata: dict,
    positive: bool = True,
    big_pad: bool = False,
    plot_cycles: bool = False,
    plot_result: bool = True,
):
    repetitions = metadata["Repetition"]
    pols = []
    for i in range(repetitions):
        df_cycle = get_half_cycle(df, metadata, i, positive=positive, plot=plot_cycles)
        polarization = get_polarization(df_cycle, metadata, big_pad=big_pad)
        pols.append(polarization)
    polarizations = np.array(pols)
    if not positive:
        polarizations *= -1

    if plot_result:
        plt.rcParams.update({"font.size": 13})
        sign = "+" if positive else "-"
        color = "r" if positive else "b"
        plt.plot(polarizations, ".-", label=rf"$P_{sign}$", color=color)
        plt.xlabel("Cycles")
        plt.ylabel(r"Polarization, $\mu C$/cm$^2$")
        plt.legend()
        plt.gca().set_ylim(0, polarizations.max() * 1.05)
    return polarizations
