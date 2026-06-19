"""FeFET transfer (Ids-Vg) sweeps with the peak gate voltage varied.

Like :mod:`probe_station.experiments.fefet_cycling`, but without endurance
cycling. Instead of pulsing between measurements, the transfer sweep's second
(peak) gate voltage ``voltage_gate_second`` is stepped across a list of values,
running one Ids(Vg) sweep per value (useful for, e.g., memory-window vs
program-voltage studies).

Both the SMU (``ids_vg_proc``) and WGFMU (``wgfmu_ids_vg_proc``) transfer
procedures are available; the recipe below uses the WGFMU one. They share the
``voltage_gate_second`` parameter and the same data columns, so either can be
swapped into the loop.
"""

import logging
import shutil
from pathlib import Path

import numpy as np
from keysight_b1530a.enums import WGFMUMeasureCurrentRange

from probe_station.experiments.common import run
from probe_station.logging_setup import add_file_log_dir, setup_file_logging
from probe_station.measurements.smu.fet_ids_vg import SmuFetIdsVgProcedure
from probe_station.measurements.wgfmu.fet_ids_vg import WgfmuFetIdsVgProcedure

folder = "results"

logger = logging.getLogger(__name__)


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
        source_channel=source,
        drain_channel=drain,
        gate_channel=gate,
        base_channel=base,
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
        gate_channel=gate,
        drain_channel=drain,
        current_range=current_range,
    )


if __name__ == "__main__":
    shutil.rmtree(Path(folder), ignore_errors=True)
    Path(folder).mkdir(exist_ok=True)
    setup_file_logging()
    add_file_log_dir(Path(folder) / "logs")

    for voltage_second in np.linspace(2.0, 10.0, 9):
        logger.info(f"=================== Gate peak voltage: {voltage_second} V ===================")
        run(
            wgfmu_ids_vg_proc(voltage_gate_second=voltage_second),
            folder=folder,
            plot=False,
            x_col="Gate Voltage",
            y_col="Drain-Source Current",
            suffix=f"_vg2={voltage_second}",
        )
