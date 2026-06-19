import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from keysight_b1530a.enums import WGFMUMeasureCurrentRange

from probe_station.experiments.common import log_points, run
from probe_station.logging_setup import add_file_log_dir, setup_file_logging
from probe_station.measurements.cmu.cv_sweep import CmuCvSweepProcedure
from probe_station.measurements.smu.iv_sweep import SmuIvSweepProcedure
from probe_station.measurements.spgu.cycling import SpguCyclingProcedure
from probe_station.measurements.wgfmu.iv_sweep import WgfmuIvSweepProcedure

folder = "results"

logger = logging.getLogger(__name__)


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
        top_voltage_first=voltage_first,
        top_voltage_second=voltage_second,
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


if __name__ == "__main__":
    shutil.rmtree(Path(folder), ignore_errors=True)
    Path(folder).mkdir(exist_ok=True)
    setup_file_logging()
    add_file_log_dir(Path(folder) / "logs")

    run(wgfmu_iv_proc(), folder=folder, plot=True, x_col="Top electrode voltage", y_col="Top electrode Current")
    run(dc_iv_proc(), folder=folder, plot=True, x_col="Voltage", y_col="Top electrode current")
    run(cv_proc(), folder=folder, plot=True, x_col="Voltage", y_col="Capacitance", timeout=120)

    total = 0
    for cycles in log_points(10, 1e10, per_decade=10):
        total += cycles
        logger.info(
            f"Total cycles (start): {total} || {datetime.now()} || {datetime.now() + timedelta(seconds=cycles * 1e-5 * 3)}"
        )

        cycling_pulse_time = 1e-5
        iv_time = 2e-4

        run(
            cycling_proc(cycles=cycles, width=cycling_pulse_time, amplitude=2.6, bipolar_pulses=True),
            folder=folder,
            timeout=60 * 60 * 24 * 3,
            startup_delay=5,
            suffix=f"_{cycles}cycles",
        )

        run(wgfmu_iv_proc(voltage_first=2.6, voltage_second=-2.6, pulse_time=iv_time), folder=folder)
        run(wgfmu_iv_proc(mode="DEFAULT", voltage_first=2.6, voltage_second=-2.6, pulse_time=iv_time), folder=folder)
        run(wgfmu_iv_proc(voltage_first=5, voltage_second=-5, pulse_time=iv_time), folder=folder)
        run(wgfmu_iv_proc(mode="DEFAULT", voltage_first=5, voltage_second=-5, pulse_time=iv_time), folder=folder)

        run(dc_iv_proc(voltage_first=2.6, voltage_second=-2.6), folder=folder)
        run(cv_proc(voltage_first=-3.2, voltage_second=3.2), folder=folder, timeout=120)
