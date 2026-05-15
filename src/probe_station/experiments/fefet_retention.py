import shutil
from pathlib import Path
from time import sleep

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from probe_station.experiments.fefet_common import cycling_proc, fet_current_proc, folder, run
from probe_station.logging_setup import add_file_log_dir, setup_file_logging


def retention(precondition_cycles=1000, amplitude=3.0, width=1e-5, delays=None, gate_read_voltage=0.0):
    """Precondition the gate with cycling, then sample the drain current at increasing delays."""
    if delays is None:
        delays = np.logspace(0, 2, num=10, base=10)

    run(
        cycling_proc(cycles=precondition_cycles, width=width, amplitude=amplitude, bipolar_pulses=True),
        timeout=60 * 60,
        startup_delay=5,
        suffix=f"_{precondition_cycles}cycles_precondition",
    )

    rows = []
    for delay in delays:
        sleep(float(delay))
        results = run(fet_current_proc(gate_voltage=gate_read_voltage), suffix=f"_delay_{delay:.3f}s")
        rows.append(
            {
                "Delay": float(delay),
                "Drain Current After Negative Pulses (A)": results.data["Drain Current"][0],
            }
        )
        pd.DataFrame(rows).to_csv(f"{folder}/retention_results.csv", index=False)

    df = pd.DataFrame(rows)

    plt.figure(figsize=(10, 6))
    plt.plot(df["Delay"], df["Drain Current After Negative Pulses (A)"], marker="o", label="Negative pulse")
    plt.xscale("log")
    plt.xlabel("Delay (s)")
    plt.ylabel("Drain Current (A)")
    plt.title("Drain Current vs Retention Delay")
    plt.grid(True)
    plt.legend()
    plt.savefig(f"{folder}/retention_plot.png")

    return df


if __name__ == "__main__":
    shutil.rmtree(Path(folder), ignore_errors=True)
    Path(folder).mkdir(exist_ok=True)
    setup_file_logging()
    add_file_log_dir(Path(folder) / "logs")

    retention()
