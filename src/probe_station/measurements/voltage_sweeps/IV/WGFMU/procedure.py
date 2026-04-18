import logging

import numpy as np
import scipy
from keysight_b1530a._bindings.config import WGFMUChannel
from keysight_b1530a._bindings.errors import get_error_summary
from keysight_b1530a.enums import (
    WGFMUMeasureCurrentRange,
)
from keysight_b1530a.errors import WGFMUError
from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    ListParameter,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.common import BaseProcedure, BaseWindow, connect_instrument, run_app
from probe_station.measurements.wgfmu_common import (
    SweepMode,
    calculate_polarization,
    get_data,
    get_sequence,
    run,
    set_waveform,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class WgfmuIvSweepProcedure(BaseProcedure):
    mode = ListParameter("Mode", default=SweepMode.PUND.name, choices=[e.name for e in SweepMode])
    pulse_time = FloatParameter("Pulse time", units="s", default=0.0001)

    voltage_top_first = FloatParameter("Top electrode voltage (first)", units="V", default=5.0)
    voltage_top_second = FloatParameter("Top electrode voltage (second)", units="V", default=-5.0)

    top = IntegerParameter("Top channel", default=2)
    current_range = ListParameter(
        "Current range",
        default=WGFMUMeasureCurrentRange.RANGE_100_UA.name,
        choices=[e.name for e in WGFMUMeasureCurrentRange],
    )

    enable_bottom = BooleanParameter("Enable bottom bias and measurement", default=False)

    voltage_bottom_first = FloatParameter(
        "Bottom electrode voltage (first)", units="V", default=-5.0, group_by="enable_bottom"
    )
    voltage_bottom_second = FloatParameter(
        "Bottom electrode voltage (second)", units="V", default=5.0, group_by="enable_bottom"
    )
    bottom = IntegerParameter("Bottom channel", default=1, group_by="enable_bottom")

    advanced_config = BooleanParameter("Advanced config", default=False)

    steps = IntegerParameter("Steps per staircase", default=100, group_by="advanced_config")
    measure_points = IntegerParameter("Points to measure", default=20_000, group_by="advanced_config")
    plot_points = IntegerParameter("Points to plot", default=1000, group_by="advanced_config")
    rise_to_hold_ratio = FloatParameter("Rise to hold time ratio", default=100, group_by="advanced_config")

    calculate_polarization = BooleanParameter("Calculate Polarization", default=False)

    pad_size = FloatParameter("Pad size", units="um", default=25, group_by="calculate_polarization")

    DATA_COLUMNS = [
        "Top electrode voltage",
        "Top electrode Current",
        "Time",
        "Bottom electrode voltage",
        "Bottom electrode current",
        "Polarization current",
        "Filtered Polarization current",
    ]

    def startup(self):
        super().startup()
        self.b1500 = connect_instrument()
        self.b1500.clear_wgfmu()
        self.ch1 = WGFMUChannel.CH1
        self.ch2 = WGFMUChannel.CH2
        self.channels = [self.ch1, self.ch2]
        self.b1500.initialize_wgfmu()

    def execute(self):
        seq = get_sequence(
            sequence_type=self.mode.lower(),
            staircase_time=self.pulse_time,
            max_voltage=self.voltage_top_first,
            min_voltage=self.voltage_top_second,
            steps=self.steps,
            rise_to_hold_ratio=self.rise_to_hold_ratio,
            trailing_pulse=True,
        )
        if self.enable_bottom:
            seq_bottom = get_sequence(
                sequence_type=self.mode.lower(),
                staircase_time=self.pulse_time,
                max_voltage=self.voltage_bottom_first,
                min_voltage=self.voltage_bottom_second,
                steps=self.steps,
                rise_to_hold_ratio=self.rise_to_hold_ratio,
                trailing_pulse=True,
            )

        set_waveform(
            b1500=self.b1500,
            sequence=seq,
            repetitions=2,
            channel=WGFMUChannel(self.top + 200),
            measure_points=self.plot_points,
        )
        if self.enable_bottom:
            set_waveform(
                b1500=self.b1500,
                sequence=seq_bottom,
                repetitions=2,
                channel=WGFMUChannel(self.bottom + 200),
                measure_points=self.plot_points,
            )

        try:
            if self.enable_bottom:
                run(
                    b1500=self.b1500,
                    channels=[self.ch1, self.ch2],
                    measure_range=WGFMUMeasureCurrentRange[self.current_range],
                )
            else:
                run(
                    b1500=self.b1500,
                    channels=[WGFMUChannel(self.top + 200)],
                    measure_range=WGFMUMeasureCurrentRange[self.current_range],
                )

            times, voltages, currents = get_data(
                b1500=self.b1500, repetitions=2, channel=WGFMUChannel(self.top + 200), points=self.plot_points
            )
            if self.enable_bottom:
                times_bottom, voltages_bottom, currents_bottom = get_data(
                    b1500=self.b1500, repetitions=2, channel=WGFMUChannel(self.bottom + 200), points=self.plot_points
                )

        except WGFMUError:
            log.error(f"{get_error_summary()}")
            self.b1500.clear_wgfmu()
            self.b1500.close_wgfmu_session()
            raise

        polarization_positive = np.concatenate(
            (
                currents[: len(currents) // 4] - currents[len(currents) // 4 : len(currents) // 2],
                np.zeros(len(currents) // 4),
            )
        )
        polarization_negative = np.concatenate(
            (
                currents[len(currents) // 2 : 3 * len(currents) // 4] - currents[3 * len(currents) // 4 :],
                np.zeros(len(currents) // 4),
            )
        )
        polarization_current = np.concatenate((polarization_positive, polarization_negative))
        filtered_polarization_current = scipy.ndimage.gaussian_filter1d(polarization_current, sigma=3)
        if self.enable_bottom:
            self.emit(
                "batch results",
                {
                    "Top electrode voltage": voltages,
                    "Top electrode Current": currents,
                    "Time": times,
                    "Bottom electrode voltage": voltages_bottom,
                    "Bottom time": times_bottom,
                    "Bottom electrode current": currents_bottom,
                    "Polarization current": polarization_current,
                    "Filtered Polarization current": filtered_polarization_current,
                },
            )
        else:
            self.emit(
                "batch results",
                {
                    "Top electrode voltage": voltages,
                    "Time": times,
                    "Top electrode Current": currents,
                    "Polarization current": polarization_current,
                    "Filtered Polarization current": filtered_polarization_current,
                },
            )
        if self.calculate_polarization:
            polarization = calculate_polarization(times, filtered_polarization_current, self.pad_size)
            log.info("Polarization (Pr): %s", polarization)

        self.b1500.close_wgfmu_session()


class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__(
            procedure_class=WgfmuIvSweepProcedure,
            logger=log,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
