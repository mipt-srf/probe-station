import logging
import sys

import numpy as np
import scipy
from keysight_b1530a._bindings.config import WGFMUChannel
from keysight_b1530a._bindings.errors import get_error_summary
from keysight_b1530a._bindings.initialization import clear, close_session, initialize, open_session
from keysight_b1530a.enums import (
    WGFMUMeasureCurrentRange,
)
from keysight_b1530a.errors import WGFMUError
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    ListParameter,
    Procedure,
)

from probe_station.measurements.voltage_sweeps.IV.WGFMU.script import (
    get_data,
    get_pund_sequence,
    run,
    set_waveform,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def calculate_polarization(times, currents, pad_size_um):
    charge = scipy.integrate.simpson(y=currents, x=times)
    area = (pad_size_um * 1e-4) ** 2
    return charge / area * 1e6


class IvSweepProcedure(Procedure):
    top = IntegerParameter("Top channel", default=2)
    bottom = IntegerParameter("Bottom channel", default=1, group_by="enable_bottom")

    voltage_top_first = FloatParameter("Top electrode voltage (first)", units="V", default=5.0)
    voltage_top_second = FloatParameter("Top electrode voltage (second)", units="V", default=-5.0)

    current_range = ListParameter(
        "Current range",
        default=WGFMUMeasureCurrentRange.RANGE_1_UA.name,
        choices=[e.name for e in WGFMUMeasureCurrentRange],
    )

    enable_bottom = BooleanParameter("Enable bottom bias and measurement", default=False)

    voltage_bottom_first = FloatParameter(
        "Bottom electrode voltage (first)", units="V", default=-5.0, group_by="enable_bottom"
    )
    voltage_bottom_second = FloatParameter(
        "Bottom electrode voltage (second)", units="V", default=5.0, group_by="enable_bottom"
    )

    pulse_time = FloatParameter("Pulse time", units="s", default=0.1)

    advanced_config = BooleanParameter("Advanced config", default=False)

    steps = IntegerParameter("Steps per staircase", default=100, group_by="advanced_config")
    measure_points = IntegerParameter("Points to measure", default=20_000, group_by="advanced_config")

    plot_points = IntegerParameter("Points to plot", default=200, group_by="advanced_config")

    rise_to_hold_ratio = FloatParameter("Rise to hold time ratio", default=0.01, group_by="advanced_config")

    calculate_polarization = BooleanParameter("Calculate Polarization", default=False)

    pad_size = FloatParameter("Pad size", units="um", default=25, group_by="calculate_polarization")

    DATA_COLUMNS = [
        "Top electrode voltage",
        "Bottom electrode voltage",
        "Time",
        "Top electrode Current",
        "Bottom electrode current",
        "Polarization current",
    ]

    def startup(self):
        clear()
        self.ch1 = WGFMUChannel.CH1
        self.ch2 = WGFMUChannel.CH2
        self.channels = [self.ch1, self.ch2]
        open_session("USB1::0x0957::0x0001::0001::0::INSTR")
        initialize()

    def execute(self):
        pund = get_pund_sequence(
            staircase_time=self.pulse_time,
            max_voltage=self.voltage_top_first,
            min_voltage=self.voltage_top_second,
            steps=self.steps,
            rise_to_hold_ratio=self.rise_to_hold_ratio,
        )
        if self.enable_bottom:
            pund_bottom = get_pund_sequence(
                staircase_time=self.pulse_time,
                max_voltage=self.voltage_bottom_first,
                min_voltage=self.voltage_bottom_second,
                steps=self.steps,
                rise_to_hold_ratio=self.rise_to_hold_ratio,
            )

        set_waveform(
            sequence=pund, repetitions=2, channel=WGFMUChannel(self.top + 200), measure_points=self.measure_points
        )
        if self.enable_bottom:
            set_waveform(
                sequence=pund_bottom,
                repetitions=2,
                channel=WGFMUChannel(self.bottom + 200),
                measure_points=self.measure_points,
            )

        try:
            if self.enable_bottom:
                run(channels=[self.ch1, self.ch2], range=WGFMUMeasureCurrentRange[self.current_range])
            else:
                run(channels=[WGFMUChannel(self.top + 200)], range=WGFMUMeasureCurrentRange[self.current_range])

            times, voltages, currents = get_data(
                repetitions=2, ch=WGFMUChannel(self.top + 200), points=self.plot_points
            )
            if self.enable_bottom:
                times_bottom, voltages_bottom, currents_bottom = get_data(
                    repetitions=2, ch=WGFMUChannel(self.bottom + 200), points=self.plot_points
                )

        except WGFMUError:
            print(get_error_summary())
            clear()
            close_session()

        polarization_positive = currents[: len(currents) // 4] - currents[len(currents) // 4 : len(currents) // 2]
        polarization_negative = (
            currents[len(currents) // 2 : 3 * len(currents) // 4] - currents[3 * len(currents) // 4 :]
        )
        polarization_current = np.concatenate(
            (polarization_positive, polarization_positive, polarization_negative, polarization_negative)
        )
        if self.enable_bottom:
            self.emit(
                "batch results",
                {
                    "Top electrode voltage": voltages,
                    "Bottom electrode voltage": voltages_bottom,
                    "Time": times,
                    "Bottom time": times_bottom,
                    "Top electrode Current": currents,
                    "Bottom electrode current": currents_bottom,
                    "Polarization current": polarization_current,
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
                },
            )
        if self.calculate_polarization:
            polarization = calculate_polarization(times, polarization_current, self.pad_size)
            log.info("Polarization (Pr): %s", polarization)

        close_session()


class MainWindow(ManagedWindowBase):
    def __init__(self):
        widget_list = (
            # TableWidget(
            #     "Experiment Table",
            #     RandomProcedure.DATA_COLUMNS,
            #     by_column=True,
            # ),
            LogWidget("Experiment Log"),
            PlotWidget("Results Graph", IvSweepProcedure.DATA_COLUMNS),
            # ImageWidget(name="Image", columns=RandomProcedure.DATA_COLUMNS, x_axis="1", y_axis="2"),
        )

        settings = [
            "pulse_time",
            "voltage_top_first",
            "voltage_top_second",
            "top",
            "current_range",
            "enable_bottom",
            "voltage_bottom_first",
            "voltage_bottom_second",
            "bottom",
            "advanced_config",
            "steps",
            "measure_points",
            "plot_points",
            "rise_to_hold_ratio",
            "calculate_polarization",
            "pad_size",
        ]

        super().__init__(
            procedure_class=IvSweepProcedure,
            inputs=settings,
            displays=settings,
            widget_list=widget_list,
        )
        logging.getLogger().addHandler(widget_list[0].handler)
        log.setLevel(self.log_level)
        log.info("ManagedWindow connected to logging")
        self.setWindowTitle("WGFMU IV (10 V)")
        self.store_measurement = False
        # self.filename = "voltage_ds={Drain-source voltage}"


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
    close_session()
