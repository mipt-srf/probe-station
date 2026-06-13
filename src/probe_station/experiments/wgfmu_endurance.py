import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from probe_station.experiments.common import log_points, run
from probe_station.logging_setup import add_file_log_dir, setup_file_logging
from probe_station.measurements.b1500 import WGFMUMeasureCurrentRange
from probe_station.measurements.wgfmu._waveforms import WaveformShape, calculate_polarization
from probe_station.measurements.wgfmu.cycling import WgfmuCyclingProcedure
from probe_station.measurements.wgfmu.iv_sweep import WgfmuIvSweepProcedure

folder = "endurance"
pad_size_um = 4

logger = logging.getLogger(__name__)


def cycling_proc(cycles=1000, width=1e-5, amplitude=2.6, channel=2, waveform_shape=WaveformShape.TRIANGLE.name):
    # DEFAULT mode runs one positive and one negative triangular sweep per repetition.
    # 50 steps keep the segments (width / steps / 2) on the WGFMU 10 ns timing grid
    # down to the 1 us cycling width.
    return WgfmuCyclingProcedure(
        repetitions=cycles,
        pulse_time=width,
        voltage_top_first=amplitude,
        voltage_top_second=-amplitude,
        top=channel,
        steps=50,
        waveform_shape=waveform_shape,
    )


def wgfmu_iv_proc(
    mode="PUND",
    voltage_first=5,
    voltage_second=-5,
    pulse_time=1e-6,
    top=2,
    bottom=1,
    current_range=WGFMUMeasureCurrentRange.RANGE_10_UA.name,
    waveform_shape=WaveformShape.TRIANGLE.name,
):
    return WgfmuIvSweepProcedure(
        voltage_top_first=voltage_first,
        voltage_top_second=voltage_second,
        pulse_time=pulse_time,
        mode=mode,
        top=top,
        enable_bottom=True,
        voltage_bottom_first=0.0,
        voltage_bottom_second=0.0,
        bottom=bottom,
        current_range=current_range,
        steps=50,
        rise_to_hold_ratio=1,
        waveform_shape=waveform_shape,
        plot_points=200,
    )


def pund_polarization_current(results):
    """P-U / N-D subtracted bottom electrode current of a PUND sweep, without filtering.

    Returns the sweep data together with the polarization current, both clipped to
    whole quarters (a partial row can be parsed while the writer is still flushing).
    """
    data = results.data[["Time", "Top electrode voltage", "Bottom electrode current"]].dropna()
    quarter = len(data) // 4
    data = data.iloc[: 4 * quarter]
    currents = data["Bottom electrode current"].to_numpy()
    positive = np.concatenate((currents[:quarter] - currents[quarter : 2 * quarter], np.zeros(quarter)))
    negative = np.concatenate((currents[2 * quarter : 3 * quarter] - currents[3 * quarter :], np.zeros(quarter)))
    return data, np.concatenate((positive, negative))


def pund_polarization(results):
    """Compute 2Pr from the unfiltered bottom electrode current of a PUND sweep."""
    data, polarization_current = pund_polarization_current(results)
    return calculate_polarization(data["Time"].to_numpy(), polarization_current, pad_size_um)


def update_polarization_plot(df):
    plt.figure(figsize=(10, 6))
    plt.plot(df["Cycles"], df["Polarization 2Pr (uC/cm^2)"], "o")
    plt.ylim(0)
    plt.xscale("log")
    plt.xlabel("Cycles")
    plt.ylabel(r"Polarization 2$P_r$ ($\mu C/cm^2$)")
    plt.title("Polarization vs Number of Cycles")
    plt.grid(True)
    plt.savefig(f"{folder}/polarization_vs_cycles.png")
    plt.close()


def plot_pund_iv(results, total_cycles):
    data, polarization_current = pund_polarization_current(results)
    plt.figure(figsize=(10, 6))
    plt.plot(data["Top electrode voltage"], data["Bottom electrode current"], label="Bottom electrode current")
    plt.plot(data["Top electrode voltage"], polarization_current, label="Polarization current")
    plt.xlabel("Top electrode voltage (V)")
    plt.ylabel("Current (A)")
    plt.title(f"PUND IV after {total_cycles} cycles")
    plt.grid(True)
    plt.legend()
    plt.savefig(f"{folder}/last_pund_iv.png")
    plt.close()


def measure_polarization(total_cycles, rows, iv_voltage, iv_time, waveform_shape=WaveformShape.TRIANGLE.name):
    """Run PUND and DEFAULT sweeps, record 2Pr, and refresh the endurance plots."""
    pund_results = run(
        wgfmu_iv_proc(
            voltage_first=iv_voltage, voltage_second=-iv_voltage, pulse_time=iv_time, waveform_shape=waveform_shape
        ),
        folder=folder,
        timeout=60 * 10,
        suffix=f"_{total_cycles}cycles_pund",
    )
    rows.append({"Cycles": total_cycles, "Polarization 2Pr (uC/cm^2)": pund_polarization(pund_results)})
    df = pd.DataFrame(rows)
    df.to_csv(f"{folder}/polarization_results.csv", index=False)
    update_polarization_plot(df)
    plot_pund_iv(pund_results, total_cycles)

    # run(
    #     wgfmu_iv_proc(
    #         mode="DEFAULT",
    #         voltage_first=iv_voltage,
    #         voltage_second=-iv_voltage,
    #         pulse_time=iv_time,
    #         waveform_shape=waveform_shape,
    #     ),
    #     folder=folder,
    #     timeout=60 * 10,
    #     suffix=f"_{total_cycles}cycles_default",
    # )


def endurance(
    cycles_schedule=None,
    amplitude=5,
    cycling_pulse_time=1e-5,
    iv_voltage=5.0,
    iv_time=1e-5,
    waveform_shape=WaveformShape.TRIANGLE.name,
):
    """Cycle the pad, running WGFMU PUND and DEFAULT sweeps after each cycling block.

    The 2Pr extracted from each PUND sweep is appended to polarization_results.csv and
    the polarization-vs-cycles plot is redrawn after every PUND measurement.
    """
    if cycles_schedule is None:
        cycles_schedule = log_points(10, 2e10, per_decade=5)

    rows = []
    total = 0
    measure_polarization(total, rows, iv_voltage, iv_time, waveform_shape=waveform_shape)

    for cycles in cycles_schedule:
        total += cycles
        logger.info(
            f"Total cycles (start): {total} || {datetime.now()} || "
            f"{datetime.now() + timedelta(seconds=cycles * cycling_pulse_time * 2)}"
        )

        run(
            cycling_proc(cycles=cycles, width=cycling_pulse_time, amplitude=amplitude, waveform_shape=waveform_shape),
            folder=folder,
            timeout=60 * 60 * 24 * 3,
            startup_delay=5,
            suffix=f"_{cycles}cycles",
        )
        measure_polarization(total, rows, iv_voltage, iv_time, waveform_shape=waveform_shape)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    shutil.rmtree(Path(folder), ignore_errors=True)
    Path(folder).mkdir(exist_ok=True)
    setup_file_logging()
    add_file_log_dir(Path(folder) / "logs")

    endurance()
