"""Shared infrastructure for experiment runner scripts.

Provides the campaign runner (:func:`run`), a quick plotting helper
(:func:`plot_results`), and the log-spaced schedule generator
(:func:`log_points`). Experiment modules import these and supply their own
``folder`` and procedure factories so each stays self-contained.
"""

import itertools
import logging
from time import sleep

import numpy as np
from matplotlib import pyplot as plt
from pymeasure.experiment import Results

from probe_station.measurements.workers import EndTimeWorker as Worker

logger = logging.getLogger(__name__)

experiment_counter = itertools.count(1)


def plot_results(results, x_col, y_col, *, log=False):
    sleep(3)
    y = np.abs(results.data[y_col]) if log else results.data[y_col]
    plt.figure(figsize=(10, 6))
    plt.plot(results.data[x_col], y)
    plt.yscale("log" if log else "linear")
    plt.xlabel(x_col)
    plt.ylabel(f"|{y_col}|" if log else y_col)
    plt.grid(True, which="both" if log else "major")
    plt.show()
    sleep(3)


def run(
    proc,
    *,
    folder="results",
    timeout=30,
    startup_delay=0,
    suffix="",
    plot=False,
    x_col=None,
    y_col=None,
    log=False,
):
    exp_num = next(experiment_counter)
    logger.info(f"=================== Measurement number: {exp_num} ===================")
    name = f"{exp_num}_{proc.__class__.__name__}{suffix}"
    results = Results(proc, f"{folder}/{name}.csv")
    worker = Worker(results)
    worker.start()
    if startup_delay:
        sleep(startup_delay)
    worker.join(timeout=timeout)

    if plot:
        plot_results(results, x_col, y_col, log=log)

    return results


def log_points(start, stop, per_decade=5):
    # Determine number of decades
    decades = int(np.log10(stop / start))
    decade_points = np.logspace(np.log10(start), np.log10(stop), decades + 1, dtype=int)

    cumsum_final = [start]
    rounded_steps = []

    # Improved rounding rule - smoother between powers of ten
    def round_nice(x):
        if x <= 0:
            return 0
        exp = int(np.floor(np.log10(x)))
        mant = x / 10**exp
        # Smoother range
        if mant < 1.3:
            mant_rounded = 1
        elif mant < 1.8:
            mant_rounded = 1.5
        elif mant < 2.5:
            mant_rounded = 2
        elif mant < 3.5:
            mant_rounded = 2.5
        elif mant < 4.5:
            mant_rounded = 3
        elif mant < 5.5:
            mant_rounded = 4
        elif mant < 6.5:
            mant_rounded = 5
        elif mant < 7.5:
            mant_rounded = 6
        elif mant < 8.5:
            mant_rounded = 7.5
        elif mant < 9.5:
            mant_rounded = 8
        else:
            mant_rounded = 10
        return int(round(mant_rounded * 10**exp, -exp + 1))  # zero out digits after first two

    # Iterate through decades
    for i in range(len(decade_points) - 1):
        a, b = decade_points[i], decade_points[i + 1]
        raw = np.logspace(np.log10(a), np.log10(b), per_decade + 1)
        steps = np.diff(raw)
        steps_rounded = [round_nice(s) for s in steps]

        # Adjust last step to hit the decade boundary exactly
        diff_to_fix = b - (a + np.sum(steps_rounded))
        steps_rounded[-1] += diff_to_fix

        for s in steps_rounded:
            rounded_steps.append(s)
            cumsum_final.append(cumsum_final[-1] + s)

    return np.array([start] + rounded_steps).astype(int).tolist()
