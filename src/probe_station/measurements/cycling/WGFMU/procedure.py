import logging

from pymeasure.experiment import IntegerParameter

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.b1500 import WGFMUMeasureCurrentRange
from probe_station.measurements.common import BaseWindow, run_app
from probe_station.measurements.wgfmu_common import (
    get_sequence,
    run_waveforms,
)
from probe_station.measurements.wgfmu_procedure import WgfmuBaseProcedure

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class WgfmuCyclingProcedure(WgfmuBaseProcedure):
    repetitions = IntegerParameter("Number of cycles", default=1e3)

    def execute(self):
        seq_top = get_sequence(
            sequence_type=self.mode.lower(),
            pulse_time=self.pulse_time,
            max_voltage=self.voltage_top_first,
            min_voltage=self.voltage_top_second,
            steps=self.steps,
            rise_to_hold_ratio=self.rise_to_hold_ratio,
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
            )

        run_waveforms(
            b1500=self.b1500,
            top_seq=seq_top,
            top_ch=self.top,
            bottom_seq=seq_bottom,
            bottom_ch=self.bottom if self.enable_bottom else None,
            repetitions=self.repetitions,
            current_range=WGFMUMeasureCurrentRange[self.current_range],
            measure=False,
        )


class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__(
            procedure_class=WgfmuCyclingProcedure,
            logger=log,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
