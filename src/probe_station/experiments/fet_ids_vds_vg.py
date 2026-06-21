"""Output characteristics: Ids(Vds) sweeps with the gate voltage varied.

Runs one :class:`SmuFetIdsVdsProcedure` Ids(Vds) sweep per gate voltage,
stepping ``gate_voltage`` across a list of values. Each sweep is saved as its
own CSV (suffixed with the gate voltage), so the family of output-characteristic
curves can be assembled in post-processing.
"""

import logging
import shutil
from pathlib import Path

import numpy as np

from probe_station.experiments.common import run
from probe_station.logging_setup import add_file_log_dir, setup_file_logging
from probe_station.measurements.smu._sweep_mode import SmuSweepMode
from probe_station.measurements.smu.fet_ids_vds import SmuFetIdsVdsProcedure

folder = "1t1c3_ids_vds_vg"

logger = logging.getLogger(__name__)


def ids_vds_proc(
    gate_voltage=0,
    first_voltage=-0.8,
    second_voltage=0.6,
    steps=100,
    mode=SmuSweepMode.START_TO_STOP.name,
    averaging=127,
    source_channel=3,
    drain_channel=1,
    gate_channel=4,
):
    return SmuFetIdsVdsProcedure(
        gate_voltage=gate_voltage,
        first_voltage=first_voltage,
        second_voltage=second_voltage,
        steps=steps,
        mode=mode,
        averaging=averaging,
        source_channel=source_channel,
        drain_channel=drain_channel,
        gate_channel=gate_channel,
    )


if __name__ == "__main__":
    shutil.rmtree(Path(folder), ignore_errors=True)
    Path(folder).mkdir(exist_ok=True)
    setup_file_logging()
    add_file_log_dir(Path(folder) / "logs")

    for gate_voltage in np.linspace(-1.0, 8.0, 91):
        logger.info(f"=================== Gate voltage: {gate_voltage} V ===================")
        run(
            ids_vds_proc(gate_voltage=gate_voltage),
            folder=folder,
            plot=False,
            x_col="Voltage",
            y_col="Source Current",
            suffix=f"_vg={gate_voltage:.3f}",
        )
