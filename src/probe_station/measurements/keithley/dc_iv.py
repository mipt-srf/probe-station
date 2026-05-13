import logging

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import FloatParameter, Parameter

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.common import BaseWindow, run_app
from probe_station.measurements.keithley.instrument import connect_instrument, set_smu
from probe_station.measurements.keithley.launcher import ADDRESS
from probe_station.measurements.keithley.pund import KeithleyPundProcedure
from probe_station.measurements.keithley.PUND_waveform import create_pulse
from probe_station.measurements.smu._widgets import IvPlotWidget

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class KeithleyDcIvProcedure(KeithleyPundProcedure):
    int_time = FloatParameter("Integration time", units="s", default=2e-2)
    current_range = FloatParameter(
        "Current range", units="A", default=1e-6, group_by="autorange", group_condition=False
    )

    _INPUTS = [
        name
        for name, obj in KeithleyPundProcedure.__dict__.items()
        if isinstance(obj, Parameter) and name not in ("space", "do_cycle", "n_precycles", "n_cycles", "hold")
    ]

    def _create_waveform(self):
        pulse_params = {"rise": self.rise, "hold": 0, "dt": 1}
        return create_pulse(pulse_params, self.vf) + create_pulse(pulse_params, self.vs)


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            IvPlotWidget("Results Graph", KeithleyDcIvProcedure.DATA_COLUMNS, x_axis="Time", y_axis="Reading"),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=KeithleyDcIvProcedure,
            widget_list=widget_list,
            inputs=KeithleyDcIvProcedure._INPUTS,
            logger=log,
        )
        from qtpy.QtWidgets import QLabel

        self._pulse_label = QLabel()
        self.inputs.layout().addWidget(self._pulse_label)
        self.inputs.rise.valueChanged.connect(self._update_pulse_duration)
        self.inputs.int_time.valueChanged.connect(self._update_pulse_duration)
        self._update_pulse_duration()

    def _update_pulse_duration(self):
        rise = self.inputs.rise.value()
        int_time = self.inputs.int_time.value()
        effective_nplc = max(0.01, int_time * 60)
        duration = round(2 * rise * effective_nplc / 60 * 1e3 * 3, 3)  # factor of 3 due to ???
        self._pulse_label.setText(f"Pulse duration: {duration} ms")


if __name__ == "__main__":
    setup_file_logging("logs")
    set_smu(connect_instrument(ADDRESS))
    run_app(MainWindow)
