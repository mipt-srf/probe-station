import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from probe_station.experiments.common import run
from probe_station.logging_setup import add_file_log_dir, setup_file_logging
from probe_station.measurements.smu.fet_ids_t import SmuFetIdsTimeProcedure
from probe_station.measurements.smu.fet_ids_vg import SmuFetIdsVgProcedure
from probe_station.measurements.spgu.cycling import SpguCyclingProcedure
from probe_station.measurements.wgfmu.cycling import WgfmuCyclingProcedure

folder = "1t1c3_retention_final_-9_smu"


def ids_vg_proc(
    voltage_ds=0.25,
    voltage_gate_first=0,
    voltage_gate_second=-9,
    points=200,
    source=3,
    drain=1,
    gate=4,
    base=2,
):
    return SmuFetIdsVgProcedure(
        voltage_ds=voltage_ds,
        voltage_gate_first=voltage_gate_first,
        voltage_gate_second=voltage_gate_second,
        points=points,
        source=source,
        drain=drain,
        gate=gate,
        base=base,
    )


def cycling_proc(cycles=10, width=1e-6, amplitude=-9.0, channel=2, bipolar_pulses=True, pulse_separation=False):
    return SpguCyclingProcedure(
        repetitions=cycles,
        width=width,
        rise=width / 10,
        tail=width / 10,
        amplitude=amplitude,
        channel=channel,
        bipolar_pulses=bipolar_pulses,
        pulse_separation=pulse_separation,
    )


def wgfmu_cycling_proc(cycles=10, width=1e-4, amplitude=8.0, channel=2, bipolar_pulses=True, pulse_separation=False):
    return WgfmuCyclingProcedure(
        repetitions=cycles,
        pulse_time=width,
        voltage_top_first=0.0,
        voltage_top_second=amplitude,
        top=channel,
    )


def fet_current_proc(
    gate_voltage=3.75,
    drain_voltage=0.25,
    source_voltage=0.0,
    base_voltage=0.0,
    gate=4,
    drain=1,
    source=3,
    base=2,
    averaging=1023,
):
    return SmuFetIdsTimeProcedure(
        gate_voltage=gate_voltage,
        drain_voltage=drain_voltage,
        source_voltage=source_voltage,
        base_voltage=base_voltage,
        gate_channel=gate,
        drain_channel=drain,
        source_channel=source,
        base_channel=base,
        averaging=averaging,
    )


def save_retention_plot(df):
    fig = plt.figure(figsize=(10, 6))
    plt.plot(df["Delay"], df["Drain Current (A)"], marker="o")
    plt.xscale("log")
    plt.xlabel("Delay (s)")
    plt.ylabel("Drain Current (A)")
    plt.title("Drain Current vs Retention Delay")
    plt.grid(True)
    plt.savefig(f"{folder}/retention_plot.png")
    plt.close(fig)


def retention(delays=None, gate_read_voltage=0.3):
    """Precondition the gate with cycling, then sample the drain current at increasing delays."""
    if delays is None:
        delays = np.logspace(-1, 2.8, num=40, base=10)

    estimated_time = sum(delays)
    estimated_finish = datetime.now() + timedelta(seconds=estimated_time)
    logging.info(f"Estimated retention time: {estimated_time:.2f}s, estimated finish: {estimated_finish}")

    # run(
    #     cycling_proc(),
    #     folder=folder,
    #     timeout=60 * 60,
    #     startup_delay=5,
    #     suffix=f"_{precondition_cycles}cycles_precondition",
    # )

    run(
        ids_vg_proc(),
        folder=folder,
        timeout=60 * 60,
        startup_delay=5,
    )

    rows = []
    for delay in delays:
        sleep(float(delay))
        results = run(
            fet_current_proc(gate_voltage=gate_read_voltage),
            folder=folder,
            timeout=60 * 60,
            suffix=f"_delay_{delay:.5f}s",
        )
        drain_current = results.data["Drain Current"]
        rows.append(
            {
                "Delay": float(delay),
                "Drain Current (A)": drain_current.iloc[-1] if not drain_current.empty else None,
            }
        )
        pd.DataFrame(rows).to_csv(f"{folder}/retention_results.csv", index=False)
        if delay > 10:
            save_retention_plot(pd.DataFrame(rows))

    df = pd.DataFrame(rows)
    save_retention_plot(df)

    return df


if __name__ == "__main__":
    shutil.rmtree(Path(folder), ignore_errors=True)
    Path(folder).mkdir(exist_ok=True)
    setup_file_logging()
    add_file_log_dir(Path(folder) / "logs")

    retention()
