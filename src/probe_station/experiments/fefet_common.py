import itertools
import logging
from time import sleep

from pymeasure.experiment import Results

from probe_station.measurements.smu.fet_ids_t import SmuFetIdsTimeProcedure
from probe_station.measurements.spgu.cycling import SpguCyclingProcedure
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


GATE = 4
DRAIN = 3
SOURCE = 2
BASE = 1


def cycling_proc(cycles=1000, width=1e-5, amplitude=3.0, channel=GATE, bipolar_pulses=True, pulse_separation=False):
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


def fet_current_proc(gate_voltage=1.0, drain_voltage=-0.5, source_voltage=0.0, base_voltage=0.0, averaging=1023):
    return SmuFetIdsTimeProcedure(
        gate_voltage=gate_voltage,
        drain_voltage=drain_voltage,
        source_voltage=source_voltage,
        base_voltage=base_voltage,
        gate_channel=GATE,
        drain_channel=DRAIN,
        source_channel=SOURCE,
        base_channel=BASE,
        averaging=averaging,
    )
