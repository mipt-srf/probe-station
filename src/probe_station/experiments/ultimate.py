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
from probe_station.measurements.cmu.cv_sweep import CmuCvSweepProcedure
from probe_station.measurements.smu.iv_sweep import SmuIvSweepProcedure
from probe_station.measurements.spgu.cycling import SpguCyclingProcedure
from probe_station.measurements.wgfmu.iv_sweep import WgfmuIvSweepProcedure
from probe_station.measurements.workers import EndTimeWorker as Worker

folder = "results"
experiment_counter = itertools.count(1)

logger = logging.getLogger(__name__)


def run(proc, *, timeout=30, startup_delay=0, suffix=""):
    exp_num = next(experiment_counter)
    logger.info(f"=================== Measurement number: {exp_num} ===================")
    name = f"{exp_num}_{proc.__class__.__name__}{suffix}"
    results = Results(proc, f"{folder}/{name}.csv")
    worker = Worker(results)
    worker.start()
    if startup_delay:
        sleep(startup_delay)
    worker.join(timeout=timeout)
    return results


def run_and_plot(proc, x_col, y_col, *, timeout=30):
    results = run(proc, timeout=timeout)
    sleep(3)
    plt.figure(figsize=(10, 6))
    plt.plot(results.data[x_col], results.data[y_col])
    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.grid(True)
    plt.show()
    sleep(3)
    return results


def cycling_proc(cycles=1000, width=1e-5, amplitude=2.6, channel=2, bipolar_pulses=True, pulse_separation=False):
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


def wgfmu_iv_proc(
    mode="PUND",
    voltage_first=5,
    voltage_second=-5,
    pulse_time=2e-4,
    top=2,
    current_range=WGFMUMeasureCurrentRange.RANGE_100_UA.name,
):
    return WgfmuIvSweepProcedure(
        voltage_top_first=voltage_first,
        voltage_top_second=voltage_second,
        pulse_time=pulse_time,
        mode=mode,
        top=top,
        current_range=current_range,
    )


def dc_iv_proc(voltage_first=-2.6, voltage_second=2.6, top_channel=4, bottom_channel=3):
    return SmuIvSweepProcedure(
        first_voltage=voltage_first,
        second_voltage=voltage_second,
        top_channel=top_channel,
        bottom_channel=bottom_channel,
    )


def cv_proc(voltage_first=-3.2, voltage_second=3.2):
    return CmuCvSweepProcedure(first_voltage=voltage_first, second_voltage=voltage_second)


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


if __name__ == "__main__":
    shutil.rmtree(Path(folder), ignore_errors=True)
    Path(folder).mkdir(exist_ok=True)
    setup_file_logging()
    add_file_log_dir(Path(folder) / "logs")

    run_and_plot(wgfmu_iv_proc(), "Top electrode voltage", "Top electrode Current")
    run_and_plot(dc_iv_proc(), "Voltage", "Top electrode current")
    run_and_plot(cv_proc(), "Voltage", "Capacitance", timeout=120)

    total = 0
    for cycles in log_points(10, 1e10, per_decade=10):
        total += cycles
        logger.info(
            f"Total cycles (start): {total} || {datetime.now()} || {datetime.now() + timedelta(seconds=cycles * 1e-5 * 3)}"
        )

        cycling_pulse_time = 1e-5
        iv_time = 1e-4

        run(
            cycling_proc(cycles=cycles, width=cycling_pulse_time, amplitude=2.6, bipolar_pulses=True),
            timeout=60 * 60 * 24 * 3,
            startup_delay=5,
            suffix=f"_{cycles}cycles",
        )

        run(wgfmu_iv_proc(voltage_first=2.6, voltage_second=-2.6, pulse_time=iv_time))
        run(wgfmu_iv_proc(mode="DEFAULT", voltage_first=2.6, voltage_second=-2.6, pulse_time=iv_time))
        run(wgfmu_iv_proc(voltage_first=5, voltage_second=-5, pulse_time=iv_time))
        run(wgfmu_iv_proc(mode="DEFAULT", voltage_first=5, voltage_second=-5, pulse_time=iv_time))

        run(dc_iv_proc(voltage_first=2.6, voltage_second=-2.6))
        run(cv_proc(voltage_first=-3.2, voltage_second=3.2), timeout=120)
