import itertools
import logging
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

import numpy as np
from matplotlib import pyplot as plt
from probe_station.measurements.cycling.PG.procedure import PgCyclingProcedure
from probe_station.measurements.voltage_sweeps.CV.procedure import CvSweepProcedure
from probe_station.measurements.voltage_sweeps.IV.SMU.built_in_procedure import (
    IvSweepProcedure,
)
from probe_station.measurements.voltage_sweeps.IV.WGFMU.procedure import (
    WgfmuIvSweepProcedure,
)
from pymeasure.experiment import Results
from pymeasure.experiment.workers import Worker

from keysight_b1530a.enums import WGFMUMeasureCurrentRange

logging.basicConfig(level=logging.INFO)
folder = "results"
Path(folder).mkdir(exist_ok=True)
experiment_counter = itertools.count(1)

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler (simpler format)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# File handler (detailed format)
log_filename = f"{folder}/experiment.log"
file_handler = logging.FileHandler(log_filename, mode='w', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)  # Can log more details to file

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

def run_cv():
    exp_num = next(experiment_counter)
    print(f"\n=================== Measurement number: {exp_num} ===================\n")
    proc = CvSweepProcedure()
    proc.first_voltage = -3.2
    proc.second_voltage = 3.2

    results = Results(proc, f"{folder}/{exp_num}_{proc.__class__.__name__}.csv")
    worker = Worker(results)
    worker.start()
    worker.join(timeout=120)


def run_dc_iv():
    exp_num = next(experiment_counter)
    print(f"\n=================== Measurement number: {exp_num} ===================\n")
    proc = IvSweepProcedure()
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
    print(f"\n=================== Measurement number: {exp_num} ===================\n")
    proc = WgfmuIvSweepProcedure()
    proc.voltage_top_first = voltage_first
    proc.voltage_top_second = voltage_second
    proc.current_range = WGFMUMeasureCurrentRange.RANGE_100_UA.name
    proc.top = 2
    proc.pulse_time = 1e-4
    proc.mode = mode
    results = Results(proc, f"{folder}/{exp_num}_{proc.__class__.__name__}.csv")
    worker = Worker(results)
    worker.start()
    worker.join(timeout=30)


def run_cycling(cycles=1000, width=1e-5):
    exp_num = next(experiment_counter)
    print(f"\n=================== Measurement number: {exp_num} ===================\n")
    proc = PgCyclingProcedure()
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

    delay_2nd = 2 * proc.width
    period = (delay_2nd + (proc.rise + proc.width + proc.tail) * 2) + delay_2nd
    duration = proc.repetitions * period

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
        return int(
            round(mant_rounded * 10**exp, -exp + 1)
        )  # zero out digits after first two

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
ds = Results.load(f"{folder}/{2}_IvSweepProcedure.csv")
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
ds = Results.load(f"{folder}/{3}_CvSweepProcedure.csv")
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
    print(
        f"Total cycles (start): {total}, || {datetime.now()} || {datetime.now() + timedelta(seconds=cycles * 1e-5 * 3)}"
    )
    run_cycling(cycles)
    run_iv_sweep(voltage_first=2.6, voltage_second=-2.6)
    run_iv_sweep(mode="DEFAULT", voltage_first=2.6, voltage_second=-2.6)
    run_iv_sweep(voltage_first=5, voltage_second=-5)
    run_iv_sweep(mode="DEFAULT", voltage_first=5, voltage_second=-5)
    run_dc_iv()
    run_cv()
    
    
    #!!!!!!!!!!!!!!!!! bipolar false
