"""FeFET endurance cycling with Vgmax-sweep characterization between batches.

Combines :mod:`probe_station.experiments.fefet_cycling` (the SPGU endurance
loop over a cumulative cycle schedule) with
:mod:`probe_station.experiments.fefet_vgmax` (a transfer sweep at each peak
gate voltage). At every stage it runs a full vgmax sweep -- one Ids(Vg) per
peak gate voltage -- then applies the next batch of cycles, so the device is
characterized vs program voltage at each point along the endurance schedule.

Each transfer file is suffixed with both the peak voltage and the cumulative
cycle count (e.g. ``_vg2=6.0_1000cycles``) so the curves can be sorted back
out during processing.

Both the SMU (``ids_vg_proc``) and WGFMU (``wgfmu_ids_vg_proc``) transfer
procedures are available; the recipe below uses the WGFMU one.
"""

import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from keysight_b1530a.enums import WGFMUMeasureCurrentRange

from probe_station.experiments.common import log_points, run
from probe_station.logging_setup import add_file_log_dir, setup_file_logging
from probe_station.measurements.smu.fet_ids_vg import SmuFetIdsVgProcedure
from probe_station.measurements.spgu.cycling import SpguCyclingProcedure
from probe_station.measurements.wgfmu.fet_ids_vg import WgfmuFetIdsVgProcedure

folder = "results"

logger = logging.getLogger(__name__)


def cycling_proc(
    cycles=1000,
    width=1e-5,
    amplitude=2.6,
    channel=2,
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

    cycling_pulse_time = 1e-5
    cycling_amplitude = 10
    peak_voltages = np.linspace(2.0, 10.0, 9)

    total = 0
    # A leading 0 gives a pristine baseline vgmax sweep before any cycling.
    for cycles in [0, *log_points(10, 1e7, per_decade=2)]:
        if cycles:
            total += cycles
            logger.info(
                f"Cycling {cycles} (total {total}) || {datetime.now()} || "
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

        for voltage_second in peak_voltages:
            run(
                wgfmu_ids_vg_proc(voltage_gate_second=voltage_second),
                folder=folder,
                plot=False,
                x_col="Gate Voltage",
                y_col="Drain-Source Current",
                suffix=f"_vg2={voltage_second}_{total}cycles",
            )
