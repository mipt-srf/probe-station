import logging
import sys
from enum import Enum

import numpy as np
import scipy
from keysight_b1530a._bindings.config import WGFMUChannel
from keysight_b1530a._bindings.errors import get_error_summary
from keysight_b1530a.enums import (
    WGFMUMeasureCurrentRange,
)
from keysight_b1530a.errors import WGFMUError
from pymeasure.display.Qt import QtWidgets
from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    ListParameter,
)
from qtpy.QtCore import QLocale
from waveform_generator import PulseSequence

from probe_station.measurements.common import BaseProcedure, BaseWindow, connect_instrument
from probe_station.measurements.cycling.WGFMU.script import (
    get_data,
    get_sequence,
    run,
    set_waveform,
)
from probe_station.utilities import setup_file_logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def calculate_polarization(times, currents, pad_size_um):
    charge = scipy.integrate.simpson(y=np.abs(currents), x=times)
    area = (pad_size_um * 1e-4) ** 2
    return charge / area * 1e6


class SweepMode(Enum):
    DEFAULT = "default"
    PUND = "pund"


class CyclingProcedure(BaseProcedure):
    mode = ListParameter("Mode", default=SweepMode.DEFAULT.name, choices=[e.name for e in SweepMode])
    pulse_time = FloatParameter("Pulse time", units="s", default=1e-5)

    voltage_top_first = FloatParameter("Top electrode voltage (first)", units="V", default=5.0)
    voltage_top_second = FloatParameter("Top electrode voltage (second)", units="V", default=-5.0)

    repetitions = IntegerParameter("Number of cycles", default=1e3)
    top = IntegerParameter("Top channel", default=2)
    current_range = ListParameter(
        "Current range",
        default=WGFMUMeasureCurrentRange.RANGE_100_UA.name,
        choices=[e.name for e in WGFMUMeasureCurrentRange],
    )

    enable_bottom = BooleanParameter("Enable bottom bias and measurement", default=False)

    voltage_bottom_first = FloatParameter(
        "Bottom electrode voltage (first)", units="V", default=-10.0, group_by="enable_bottom"
    )
    voltage_bottom_second = FloatParameter(
        "Bottom electrode voltage (second)", units="V", default=10.0, group_by="enable_bottom"
    )
    bottom = IntegerParameter("Bottom channel", default=1, group_by="enable_bottom")

    advanced_config = BooleanParameter("Advanced config", default=False)

    steps = IntegerParameter("Steps per staircase", default=100, group_by="advanced_config")
    rise_to_hold_ratio = FloatParameter("Rise to hold time ratio", default=1, group_by="advanced_config")

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
        self.b1500 = connect_instrument(timeout=60000, reset=False)
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
            steps=self.steps // 2,
            rise_to_hold_ratio=self.rise_to_hold_ratio,
        )
        if self.enable_bottom:
            seq_bottom = get_sequence(
                sequence_type=self.mode.lower(),
                staircase_time=self.pulse_time,
                max_voltage=self.voltage_bottom_first,
                min_voltage=self.voltage_bottom_second,
                steps=self.steps // 2,
                rise_to_hold_ratio=self.rise_to_hold_ratio,
            )

        if (
            self.enable_bottom
            and max(
                abs(self.voltage_top_first - self.voltage_top_second),
                abs(self.voltage_bottom_first - self.voltage_bottom_second),
            )
            > 10
        ):
            seq_pu = PulseSequence(seq.pulses[:4])
            seq_nd = PulseSequence(seq.pulses[4:])

            seq_bottom_pu = PulseSequence(seq_bottom.pulses[:4])
            seq_bottom_nd = PulseSequence(seq_bottom.pulses[4:])

            set_waveform(
                b1500=self.b1500,
                sequence=seq_pu,
                repetitions=1,
                channel=WGFMUChannel(self.top + 200),
                measure_points=self.steps * 2,
                pattern_name="top_pu",
            )
            set_waveform(
                b1500=self.b1500,
                sequence=seq_bottom_pu,
                repetitions=1,
                channel=WGFMUChannel(self.bottom + 200),
                measure_points=self.steps * 2,
                pattern_name="bottom_pu",
            )

            try:
                run(b1500=self.b1500, channels=[self.ch1, self.ch2], range=WGFMUMeasureCurrentRange[self.current_range])

                times, voltages, currents = get_data(
                    b1500=self.b1500, repetitions=1, ch=WGFMUChannel(self.top + 200), points=self.steps * 2
                )
                times_bottom, voltages_bottom, currents_bottom = get_data(
                    b1500=self.b1500, repetitions=1, ch=WGFMUChannel(self.bottom + 200), points=self.steps * 4
                )

            except WGFMUError:
                log.error(f"{get_error_summary()}")
                self.b1500.clear_wgfmu()
                self.b1500.close_wgfmu_session()

            self.b1500.clear_wgfmu()

            set_waveform(
                sequence=seq_nd,
                repetitions=1,
                channel=WGFMUChannel(self.top + 200),
                measure_points=self.steps * 2,
                pattern_name="top_nd",
            )
            set_waveform(
                sequence=seq_bottom_nd,
                repetitions=1,
                channel=WGFMUChannel(self.bottom + 200),
                measure_points=self.steps * 2,
                pattern_name="bottom_nd",
            )

            try:
                run(b1500=self.b1500, channels=[self.ch1, self.ch2], range=WGFMUMeasureCurrentRange[self.current_range])

                times_nd, voltages_nd, currents_nd = get_data(
                    b1500=self.b1500, repetitions=1, ch=WGFMUChannel(self.top + 200), points=self.steps * 2
                )
                times_bottom_nd, voltages_bottom_nd, currents_bottom_nd = get_data(
                    b1500=self.b1500, repetitions=1, ch=WGFMUChannel(self.bottom + 200), points=self.steps * 4
                )

            except WGFMUError:
                log.error(f"{get_error_summary()}")
                self.b1500.clear_wgfmu()
                self.b1500.close_wgfmu_session()

            voltages = np.concatenate((voltages, voltages_nd))
            currents = np.concatenate((currents, currents_nd))
            times = np.concatenate((times, times_nd))
            voltages_bottom = np.concatenate((voltages_bottom, voltages_bottom_nd))
            currents_bottom = np.concatenate((currents_bottom, currents_bottom_nd))
            times_bottom = np.concatenate((times_bottom, times_bottom_nd))

            self.emit(
                "batch results",
                {
                    "Top electrode voltage": voltages,
                    "Top electrode Current": currents,
                    "Time": times,
                    "Bottom electrode voltage": voltages_bottom,
                    "Bottom time": times_bottom,
                    "Bottom electrode current": currents_bottom,
                },
            )

        else:
            set_waveform(
                sequence=seq,
                repetitions=self.repetitions,
                channel=WGFMUChannel(self.top + 200),
                measure_points=self.steps * 4,
            )
            if self.enable_bottom:
                set_waveform(
                    sequence=seq_bottom,
                    repetitions=self.repetitions,
                    channel=WGFMUChannel(self.bottom + 200),
                    measure_points=self.steps * 4,
                )

            try:
                if self.enable_bottom:
                    run(channels=[self.ch1, self.ch2], range=WGFMUMeasureCurrentRange[self.current_range])
                else:
                    run(channels=[WGFMUChannel(self.top + 200)], range=WGFMUMeasureCurrentRange[self.current_range])

                # times, voltages, currents = get_data(
                #     b1500=self.b1500, repetitions=1, ch=WGFMUChannel(self.top + 200), points=self.steps*4
                # )
                # if self.enable_bottom:
                #     times_bottom, voltages_bottom, currents_bottom = get_data(
                #         b1500=self.b1500, repetitions=1, ch=WGFMUChannel(self.bottom + 200), points=self.steps*4
                #     )

            except WGFMUError:
                log.error(f"{get_error_summary()}")
                self.b1500.clear_wgfmu()
                self.b1500.close_wgfmu_session()

            # polarization_positive = np.concatenate(
            #     (
            #         currents[: len(currents) // 4] - currents[len(currents) // 4 : len(currents) // 2],
            #         np.zeros(len(currents) // 4),
            #     )
            # )
            # polarization_negative = np.concatenate(
            #     (
            #         currents[len(currents) // 2 : 3 * len(currents) // 4] - currents[3 * len(currents) // 4 :],
            #         np.zeros(len(currents) // 4),
            #     )
            # )
            # polarization_current = np.concatenate((polarization_positive, polarization_negative))
            # filtered_polarization_current = scipy.ndimage.gaussian_filter1d(polarization_current, sigma=3)
            # if self.enable_bottom:
            #     self.emit(
            #         "batch results",
            #         {
            #             "Top electrode voltage": voltages,
            #             "Top electrode Current": currents,
            #             "Time": times,
            #             "Bottom electrode voltage": voltages_bottom,
            #             "Bottom time": times_bottom,
            #             "Bottom electrode current": currents_bottom,
            #             "Polarization current": polarization_current,
            #             "Filtered Polarization current": filtered_polarization_current,
            #         },
            #     )
            # else:
            #     self.emit(
            #         "batch results",
            #         {
            #             "Top electrode voltage": voltages,
            #             "Time": times,
            #             "Top electrode Current": currents,
            #             "Polarization current": polarization_current,
            #             "Filtered Polarization current": filtered_polarization_current,
            #         },
            #     )
            # if self.calculate_polarization:
            #     polarization = calculate_polarization(times, filtered_polarization_current, self.pad_size)
            #     log.info("Polarization (Pr): %s", polarization)

        self.b1500.close_wgfmu_session()


class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__(
            procedure_class=CyclingProcedure,
            logger=log,
        )
        self.store_measurement = False


if __name__ == "__main__":
    setup_file_logging("logs")
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
