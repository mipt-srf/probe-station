import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from keysight_b1530a.enums import WGFMUMeasureCurrentRange

from probe_station.experiments.common import log_points, run
from probe_station.logging_setup import add_file_log_dir, setup_file_logging
from probe_station.measurements.smu.fet_ids_vg import SmuFetIdsVgProcedure
from probe_station.measurements.spgu.cycling import SpguCyclingProcedure
from probe_station.measurements.wgfmu.fet_ids_vg import WgfmuFetIdsVgProcedure

folder = "results"

logger = logging.getLogger(__name__)

GATE_SPGU_CHANNEL = 2


def cycling_proc(
    cycles=1000,
    width=1e-5,
    amplitude=2.6,
    channel=GATE_SPGU_CHANNEL,
    bipolar_pulses=True,
    pulse_separation=False,
):
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


def ids_vg_proc(
    voltage_ds=0.25,
    voltage_gate_first=0,
    voltage_gate_second=4,
    points=100,
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


def wgfmu_ids_vg_proc(
    voltage_ds=0.25,
    voltage_gate_first=0,
    voltage_gate_second=10,
    pulse_time=1e-3,
    mode="DEFAULT",
    gate=2,
    drain=1,
    current_range=WGFMUMeasureCurrentRange.RANGE_10_MA.name,
):
    return WgfmuFetIdsVgProcedure(
        voltage_ds=voltage_ds,
        voltage_gate_first=voltage_gate_first,
        voltage_gate_second=voltage_gate_second,
        pulse_time=pulse_time,
        mode=mode,
        gate=gate,
        drain=drain,
        current_range=current_range,
    )


if __name__ == "__main__":
    shutil.rmtree(Path(folder), ignore_errors=True)
    Path(folder).mkdir(exist_ok=True)
    setup_file_logging()
    add_file_log_dir(Path(folder) / "logs")

    cycling_pulse_time = 1e-3
    cycling_amplitude = 10

    run(wgfmu_ids_vg_proc(), folder=folder, plot=False, x_col="Gate Voltage", y_col="Drain-Source Current")

    total = 0
    for cycles in log_points(10, 1e7, per_decade=2):
        total += cycles
        logger.info(
            f"Total cycles (start): {total} || {datetime.now()} || "
            f"{datetime.now() + timedelta(seconds=cycles * cycling_pulse_time * 3)}"
        )

        run(
            cycling_proc(
                cycles=cycles,
                width=cycling_pulse_time,
                amplitude=cycling_amplitude,
                bipolar_pulses=True,
            ),
            folder=folder,
            timeout=60 * 60 * 24 * 3,
            startup_delay=5,
            suffix=f"_{cycles}cycles",
        )

        run(wgfmu_ids_vg_proc(), folder=folder, plot=False, x_col="Gate Voltage", y_col="Drain-Source Current")
