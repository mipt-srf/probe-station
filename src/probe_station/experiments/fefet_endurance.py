import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from probe_station.experiments.fefet_common import cycling_proc, fet_current_proc, folder, run
from probe_station.logging_setup import add_file_log_dir, setup_file_logging


def endurance(cycles_schedule=None, amplitude=8.0, width=1e-5):
    """Cycle the gate, then measure FET current after a negative-state and a positive-state write.

    For each cycle count in ``cycles_schedule``: run bipolar cycling, measure drain current
    (state after the final negative pulse), apply a single positive pulse, measure again.
    """
    if cycles_schedule is None:
        cycles_schedule = np.logspace(0, 6, num=6 * 3, base=10, dtype=int)

    currents_after_neg = np.zeros(len(cycles_schedule))
    currents_after_pos = np.zeros(len(cycles_schedule))

    for i, cycles in enumerate(cycles_schedule):
        run(
            cycling_proc(cycles=cycles, width=width, amplitude=amplitude, bipolar_pulses=True),
            timeout=60 * 60 * 24,
            startup_delay=5,
            suffix=f"_{cycles}cycles_bipolar",
        )
        neg_results = run(fet_current_proc(), suffix=f"_{cycles}cycles_after_neg")
        currents_after_neg[i] = neg_results.data["Drain Current"][0]

        run(
            cycling_proc(cycles=1, width=width / 2, amplitude=amplitude, bipolar_pulses=False),
            timeout=60,
            suffix=f"_{cycles}cycles_unipolar",
        )
        pos_results = run(fet_current_proc(), suffix=f"_{cycles}cycles_after_pos")
        currents_after_pos[i] = pos_results.data["Drain Current"][0]

    df = pd.DataFrame(
        {
            "Cycles": cycles_schedule,
            "Drain Current After Negative Pulses (A)": currents_after_neg,
            "Drain Current After Positive Pulses (A)": currents_after_pos,
        }
    )
    df.to_csv(f"{folder}/endurance_results.csv", index=False)

    plt.figure(figsize=(10, 6))
    plt.plot(cycles_schedule, currents_after_neg, marker="o", label="Negative pulse")
    plt.plot(cycles_schedule, currents_after_pos, marker="o", label="Positive pulse")
    plt.xscale("log")
    plt.xlabel("Number of Cycles")
    plt.ylabel("Drain Current (A)")
    plt.title("Drain Current vs Number of Cycles")
    plt.grid(True)
    plt.legend()
    plt.savefig(f"{folder}/endurance_plot.png")

    return df


if __name__ == "__main__":
    shutil.rmtree(Path(folder), ignore_errors=True)
    Path(folder).mkdir(exist_ok=True)
    setup_file_logging()
    add_file_log_dir(Path(folder) / "logs")

    endurance()
