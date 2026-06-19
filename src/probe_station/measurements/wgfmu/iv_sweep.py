import logging

import scipy
from pymeasure.display.widgets import PlotWidget
from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    ListParameter,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.b1500 import WGFMUMeasureCurrentRange
from probe_station.measurements.pymeasure_base import BaseWindow, run_app
from probe_station.measurements.wgfmu._base import WgfmuBaseProcedure
from probe_station.measurements.wgfmu._waveforms import (
    SweepMode,
    WaveformShape,
    calculate_polarization,
    get_sequence,
    pund_polarization_current,
    run_waveforms,
    run_waveforms_split,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class WgfmuIvSweepProcedure(WgfmuBaseProcedure):
    mode = ListParameter("Mode", default=SweepMode.PUND.name, choices=[e.name for e in SweepMode])
    pulse_time = FloatParameter("Pulse time", units="s", default=2e-4)

    current_range = ListParameter(
        "Current range",
        default=WGFMUMeasureCurrentRange.RANGE_100_UA.name,
        choices=[e.name for e in WGFMUMeasureCurrentRange],
    )
    bottom_current_range = ListParameter(
        "Bottom current range",
        default=WGFMUMeasureCurrentRange.RANGE_100_UA.name,
        choices=[e.name for e in WGFMUMeasureCurrentRange],
        group_by="enable_bottom",
    )

    steps = IntegerParameter("Steps per pulse", default=200, group_by="advanced_config")
    waveform_shape = ListParameter(
        "Waveform shape",
        default=WaveformShape.STAIRCASE.name,
        choices=[e.name for e in WaveformShape],
        group_by="advanced_config",
    )
    rise_to_hold_ratio = FloatParameter("Rise to hold time ratio", default=100, group_by="advanced_config")

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
            first_voltage=self.top_voltage_first,
            second_voltage=self.top_voltage_second,
            steps=self.steps,
            rise_to_hold_ratio=self.rise_to_hold_ratio,
            shape=self.waveform_shape.lower(),
            trailing_pulse=True,
        )
        seq_bottom = None
        if self.enable_bottom:
            seq_bottom = get_sequence(
                sequence_type=self.mode.lower(),
                pulse_time=self.pulse_time,
                first_voltage=self.bottom_voltage_first,
                second_voltage=self.bottom_voltage_second,
                steps=self.steps,
                rise_to_hold_ratio=self.rise_to_hold_ratio,
                shape=self.waveform_shape.lower(),
                trailing_pulse=True,
            )

        top_span = abs(self.top_voltage_first - self.top_voltage_second)
        bottom_span = abs(self.bottom_voltage_first - self.bottom_voltage_second) if self.enable_bottom else 0
        high_voltage = max(top_span, bottom_span) > 10

        if high_voltage:
            if not self.enable_bottom:
                raise ValueError("Pulses exceeding 10 V require the bottom electrode to be enabled")
            logger.warning("High voltage mode is enabled. Current measurement might be inaccurate")
            top_data, bottom_data = run_waveforms_split(
                b1500=self.b1500,
                top_seq=seq_top,
                top_ch=self.top,
                bottom_seq=seq_bottom,
                bottom_ch=self.bottom,
                current_range=WGFMUMeasureCurrentRange[self.current_range],
                bottom_current_range=WGFMUMeasureCurrentRange[self.bottom_current_range],
                plot_points=self.plot_points,
            )
        else:
            result = run_waveforms(
                b1500=self.b1500,
                top_seq=seq_top,
                top_ch=self.top,
                bottom_seq=seq_bottom,
                bottom_ch=self.bottom if self.enable_bottom else None,
                repetitions=1,
                current_range=WGFMUMeasureCurrentRange[self.current_range],
                bottom_current_range=WGFMUMeasureCurrentRange[self.bottom_current_range],
                measure=True,
                plot_points=self.plot_points,
            )
            top_data, bottom_data = result

        times, voltages, currents = top_data

        data = {
            "Top electrode voltage": voltages,
            "Top electrode Current": currents,
            "Time": times,
        }
        if bottom_data is not None:
            _, voltages_bottom, currents_bottom = bottom_data
            data["Bottom electrode voltage"] = voltages_bottom
            data["Bottom electrode current"] = currents_bottom

        # The P-U / N-D subtraction assumes the four equal PUND quarters; in
        # DEFAULT mode there are only two pulses and the result is meaningless.
        is_pund = self.mode == SweepMode.PUND.name
        filtered_polarization_current = None
        if is_pund:
            polarization_current = pund_polarization_current(voltages, currents)
            filtered_polarization_current = scipy.ndimage.gaussian_filter1d(polarization_current, sigma=3)
            data["Polarization current"] = polarization_current
            data["Filtered Polarization current"] = filtered_polarization_current

        self.emit("batch results", data)

        if self.compute_polarization:
            if is_pund:
                polarization = calculate_polarization(times, filtered_polarization_current, self.pad_size)
                logger.info("Polarization (2Pr): %s", polarization)
            else:
                logger.warning("Polarization calculation requires PUND mode; skipping")


class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__(
            procedure_class=WgfmuIvSweepProcedure,
            logger=logger,
        )
        # temporary bug fix for incorrect autoscaling in the plot
        plot = next(w for w in self.widget_list if isinstance(w, PlotWidget))
        plot.plot.setXRange(-10, 10, padding=0)
        plot.plot.setLimits(xMin=-10, xMax=10)


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
