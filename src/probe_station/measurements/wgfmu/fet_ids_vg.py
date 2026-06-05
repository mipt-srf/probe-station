import logging

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.b1500 import WGFMUMeasureCurrentRange
from probe_station.measurements.pymeasure_base import BaseWindow, run_app
from probe_station.measurements.smu._widgets import IvPlotWidget
from probe_station.measurements.wgfmu._base import WgfmuSweepProcedure
from probe_station.measurements.wgfmu._waveforms import (
    get_constant_sequence,
    get_sequence,
    run_waveforms,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class WgfmuFetIdsVgProcedure(WgfmuSweepProcedure):
    """FET transfer (Ids-Vg) sweep on the WGFMU.

    The gate channel is driven with a triangular voltage sweep while the drain
    channel is held at a constant Vds. Both channels measure current at aligned
    time points, so the drain current sampled against the gate voltage gives the
    transfer curve. Mirrors the SMU ``Ids (Vg)`` procedure but uses the fast
    WGFMU waveform path like the WGFMU IV sweep.
    """

    gate = IntegerParameter("Gate channel", default=2)
    drain = IntegerParameter("Drain channel", default=1)

    voltage_ds = FloatParameter("Drain-source voltage", units="V", default=1.0)
    voltage_gate_first = FloatParameter("Gate voltage (first)", units="V", default=-5.0)
    voltage_gate_second = FloatParameter("Gate voltage (second)", units="V", default=5.0)

    plot_points = IntegerParameter("Points to plot", default=1000, group_by="advanced_config")

    DATA_COLUMNS = ["Gate Voltage", "Drain-Source Current", "Gate Current", "Time"]

    def execute(self):
        seq_gate = get_sequence(
            sequence_type=self.mode.lower(),
            pulse_time=self.pulse_time,
            max_voltage=self.voltage_gate_first,
            min_voltage=self.voltage_gate_second,
            steps=self.steps,
            rise_to_hold_ratio=self.rise_to_hold_ratio,
        )
        seq_drain = get_constant_sequence(self.voltage_ds, seq_gate.total_duration)

        gate_data, drain_data = run_waveforms(
            b1500=self.b1500,
            top_seq=seq_gate,
            top_ch=self.gate,
            bottom_seq=seq_drain,
            bottom_ch=self.drain,
            repetitions=1,
            current_range=WGFMUMeasureCurrentRange[self.current_range],
            measure=True,
            plot_points=self.plot_points,
        )

        times, gate_voltages, gate_currents = gate_data
        _, _, drain_currents = drain_data

        self.emit(
            "batch results",
            {
                "Gate Voltage": gate_voltages,
                "Drain-Source Current": drain_currents,
                "Gate Current": gate_currents,
                "Time": times,
            },
        )


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            IvPlotWidget("Results Graph", WgfmuFetIdsVgProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=WgfmuFetIdsVgProcedure,
            widget_list=widget_list,
            logger=log,
        )
        self.setWindowTitle("Ids (Vg) - WGFMU")
        self.filename = "voltage_ds={Drain-source voltage}"


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
