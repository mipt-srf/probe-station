import logging

import numpy as np
import scipy
from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    ListParameter,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.common import BaseWindow, run_app
from probe_station.measurements.wgfmu_common import (
    SweepMode,
    WgfmuBaseProcedure,
    calculate_polarization,
    get_sequence,
    run_waveforms,
    run_waveforms_split,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class WgfmuIvSweepProcedure(WgfmuBaseProcedure):
    mode = ListParameter("Mode", default=SweepMode.PUND.name, choices=[e.name for e in SweepMode])
    pulse_time = FloatParameter("Pulse time", units="s", default=2e-4)

    steps = IntegerParameter("Steps per pulse", default=200, group_by="advanced_config")
    rise_to_hold_ratio = FloatParameter("Rise to hold time ratio", default=100, group_by="advanced_config")

    measure_points = IntegerParameter("Points to measure", default=20_000, group_by="advanced_config")
    plot_points = IntegerParameter("Points to plot", default=1000, group_by="advanced_config")

    compute_polarization = BooleanParameter("Calculate Polarization", default=False)
    pad_size = FloatParameter("Pad size", units="um", default=25, group_by="compute_polarization")

    DATA_COLUMNS = [
        "Top electrode voltage",
        "Top electrode Current",
        "Time",
        "Bottom electrode voltage",
        "Bottom electrode current",
        "Polarization current",
        "Filtered Polarization current",
    ]

    def execute(self):
        seq_top = get_sequence(
            sequence_type=self.mode.lower(),
            pulse_time=self.pulse_time,
            max_voltage=self.voltage_top_first,
            min_voltage=self.voltage_top_second,
            steps=self.steps,
            rise_to_hold_ratio=self.rise_to_hold_ratio,
            trailing_pulse=True,
        )
        seq_bottom = None
        if self.enable_bottom:
            seq_bottom = get_sequence(
                sequence_type=self.mode.lower(),
                pulse_time=self.pulse_time,
                max_voltage=self.voltage_bottom_first,
                min_voltage=self.voltage_bottom_second,
                steps=self.steps,
                rise_to_hold_ratio=self.rise_to_hold_ratio,
                trailing_pulse=True,
            )

        top_span = abs(self.voltage_top_first - self.voltage_top_second)
        bottom_span = abs(self.voltage_bottom_first - self.voltage_bottom_second) if self.enable_bottom else 0
        high_voltage = max(top_span, bottom_span) > 10

        if high_voltage:
            if not self.enable_bottom:
                raise ValueError("Pulses exceeding 10 V require the bottom electrode to be enabled")
            top_data, bottom_data = run_waveforms_split(
                b1500=self.b1500,
                top_seq=seq_top,
                top_ch=self.top,
                bottom_seq=seq_bottom,
                bottom_ch=self.bottom,
                current_range=self.measure_current_range,
                plot_points=self.plot_points,
            )
        else:
            result = run_waveforms(
                b1500=self.b1500,
                top_seq=seq_top,
                top_ch=self.top,
                bottom_seq=seq_bottom,
                bottom_ch=self.bottom if self.enable_bottom else None,
                repetitions=2,
                current_range=self.measure_current_range,
                measure=True,
                plot_points=self.plot_points,
            )
            top_data, bottom_data = result

        times, voltages, currents = top_data

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

        if bottom_data is not None:
            times_bottom, voltages_bottom, currents_bottom = bottom_data
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
        if self.compute_polarization:
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
