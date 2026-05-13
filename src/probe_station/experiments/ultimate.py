import itertools
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

import numpy as np
from keysight_b1530a.enums import WGFMUMeasureCurrentRange
from matplotlib import pyplot as plt
from pymeasure.experiment import Results

from probe_station.logging_setup import add_file_log_dir, setup_file_logging
from probe_station.measurements.cycling.PG.cycling import SpguCyclingProcedure
from probe_station.measurements.voltage_sweeps.CV.cv_sweep import CmuCvSweepProcedure
from probe_station.measurements.voltage_sweeps.IV.SMU.iv_sweep import (
    SmuIvSweepProcedure,
)
from probe_station.measurements.voltage_sweeps.IV.WGFMU.iv_sweep import (
    WgfmuIvSweepProcedure,
)
from probe_station.measurements.workers import EndTimeWorker as Worker

folder = "results"
experiment_counter = itertools.count(1)

logger = logging.getLogger(__name__)


def run_cv():
    exp_num = next(experiment_counter)
    logger.info(f"=================== Measurement number: {exp_num} ===================")
    proc = CmuCvSweepProcedure()
    proc.first_voltage = -3.2
    proc.second_voltage = 3.2

    results = Results(proc, f"{folder}/{exp_num}_{proc.__class__.__name__}.csv")
    worker = Worker(results)
    worker.start()
    worker.join(timeout=120)


def run_dc_iv():
    exp_num = next(experiment_counter)
    logger.info(f"=================== Measurement number: {exp_num} ===================")
    proc = SmuIvSweepProcedure()
    proc.first_voltage = -2.6
    proc.second_voltage = 2.6
    proc.top_channel = 4
    proc.bottom_channel = 3

    results = Results(proc, f"{folder}/{exp_num}_{proc.__class__.__name__}.csv")
    worker = Worker(results)
    worker.start()
    worker.join(timeout=30)


def run_iv_sweep(mode="PUND", voltage_first=5, voltage_second=-5):
    exp_num = next(experiment_counter)
    logger.info(f"=================== Measurement number: {exp_num} ===================")
    proc = WgfmuIvSweepProcedure()
    proc.voltage_top_first = voltage_first
    proc.voltage_top_second = voltage_second
    proc.current_range = WGFMUMeasureCurrentRange.RANGE_100_UA.name
    proc.top = 2
    proc.pulse_time = 2e-4
    proc.mode = mode
    results = Results(proc, f"{folder}/{exp_num}_{proc.__class__.__name__}.csv")
    worker = Worker(results)
    worker.start()
    worker.join(timeout=30)


def run_cycling(cycles=1000, width=1e-5):
    exp_num = next(experiment_counter)
    logger.info(f"=================== Measurement number: {exp_num} ===================")
    proc = SpguCyclingProcedure()
    proc.width = width
    proc.repetitions = cycles
    proc.amplitude = 2.6
    proc.bipolar_pulses = False
    proc.channel = 2
    proc.pulse_separation = False
    proc.rise = width / 10
    proc.tail = width / 10

    results = Results(proc, f"{folder}/{exp_num}_{proc.__class__.__name__}_{cycles}cycles.csv")
    worker = Worker(results)
    worker.start()

    # delay_2nd = 2 * proc.width
    # period = (delay_2nd + (proc.rise + proc.width + proc.tail) * 2) + delay_2nd
    # duration = proc.repetitions * period
    # sleep(duration * 1.5)

    sleep(5)

    worker.join(timeout=60 * 60 * 24 * 3)


def log_points(start, stop, per_decade=5):
    # Determine number of decades
    decades = int(np.log10(stop / start))
    decade_points = np.logspace(np.log10(start), np.log10(stop), decades + 1, dtype=int)

    cumsum_final = [start]
    rounded_steps = []

    # Improved rounding rule — smoother between powers of ten
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

    return np.array([start] + rounded_steps).astype(int)


# log_points(10, 1000, per_decade=2) # From 10 to 1000, with 2 additional points per decade (so 3 points: 10, p1, p2, 100,)


if __name__ == "__main__":
    shutil.rmtree(Path(folder), ignore_errors=True)
    Path(folder).mkdir(exist_ok=True)
    setup_file_logging()
    add_file_log_dir(Path(folder) / "logs")

    # run_cycling(100)
    # run_iv_sweep()

    # run_dc_iv()

    # run_cv()

    experiment_counter = itertools.count(1)
    run_iv_sweep()
    sleep(3)
    plt.figure(figsize=(10, 6))
    ds = Results.load(f"{folder}/{1}_WgfmuIvSweepProcedure.csv")
    plt.plot(
        ds.data["Top electrode voltage"],
        ds.data["Top electrode Current"],
    )

    plt.xlabel("Voltage")
    plt.ylabel("Top electrode current")
    plt.legend()
    plt.grid(True)
    plt.show()
    sleep(3)

    run_dc_iv()

    plt.figure(figsize=(10, 6))
    ds = Results.load(f"{folder}/{2}_SmuIvSweepProcedure.csv")
    plt.plot(
        ds.data["Voltage"],
        ds.data["Top electrode current"],
    )

    plt.xlabel("Voltage")
    plt.ylabel("Top electrode current")
    plt.legend()
    plt.grid(True)
    plt.show()
    sleep(3)

    run_cv()

    plt.figure(figsize=(10, 6))
    ds = Results.load(f"{folder}/{3}_CmuCvSweepProcedure.csv")
    plt.plot(
        ds.data["Voltage"],
        ds.data["Capacitance"],
    )

    plt.xlabel("Voltage")
    plt.ylabel("Top electrode current")
    plt.legend()
    plt.grid(True)
    plt.show()
    sleep(3)
    total = 0
    for cycles in [
        # *[25] * 4,
        # *[100] * 9,
        # *[1000] * 9,
        # *[10000] * 9,
        # *[100_000] * 9,
        # *[1_000_000] * 999,
        # *log_points(10, 1e6, per_decade=4).tolist(),
        *log_points(10, 1e10, per_decade=10).tolist()[:],
        # *[1_000_000] * 999,
        # *[1_000_000] * 1000,
        # *[10**7] * 100
    ]:
        cycles = int(cycles)
        total += cycles
        logger.info(
            f"Total cycles (start): {total} || {datetime.now()} || {datetime.now() + timedelta(seconds=cycles * 1e-5 * 3)}"
        )
        run_cycling(cycles)
        run_iv_sweep(voltage_first=2.6, voltage_second=-2.6)
        run_iv_sweep(mode="DEFAULT", voltage_first=2.6, voltage_second=-2.6)
        run_iv_sweep(voltage_first=5, voltage_second=-5)
        run_iv_sweep(mode="DEFAULT", voltage_first=5, voltage_second=-5)
        run_dc_iv()
        run_cv()

        #!!!!!!!!!!!!!!!!! bipolar false
