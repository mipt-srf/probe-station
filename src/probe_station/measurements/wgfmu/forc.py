"""WGFMU first-order reversal curve (FORC) measurement.

A FORC measurement records a family of triangular sweeps that all start and end
at positive saturation and reverse at a descending series of reversal voltages
(Schenk et al. 2015, *Complex Internal Bias Fields in Ferroelectric Hafnium
Oxide*). The whole family is driven as a single continuous waveform on one WGFMU
channel and measured in one FASTIV run, then split back into per-curve segments
that are stored in long (tidy) form: each row carries the reversal voltage of the
curve it belongs to, so the switching density can be derived offline.

This module implements the raw measurement only; deriving the experimental
Preisach / switching-density plot from the saved curves is done separately in the
analysis package.
"""

import logging

import numpy as np
from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    ListParameter,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.b1500 import WGFMUMeasureCurrentRange
from probe_station.measurements.pymeasure_base import BasePlotWidget, BaseWindow, run_app
from probe_station.measurements.wgfmu._base import WgfmuProcedure
from probe_station.measurements.wgfmu._waveforms import (
    get_forc_sequence,
    run_waveforms,
    split_forc_record,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class WgfmuForcProcedure(WgfmuProcedure):
    """Measure a first-order reversal curve (FORC) family on one WGFMU channel.

    Parameters are declared in GUI order (see :class:`WgfmuProcedure`). The
    measurement is top-electrode only; the bottom electrode is held by the
    instrument's default grounding.
    """

    max_voltage = FloatParameter("Saturation voltage", units="V", default=4.0)
    min_reversal_voltage = FloatParameter("Minimum reversal voltage", units="V", default=-4.0)
    grid_steps = IntegerParameter("Number of reversal curves", default=60)
    pulse_time = FloatParameter("Full-depth ramp time", units="s", default=2e-4)

    top = IntegerParameter("Top channel", default=2)

    current_range = ListParameter(
        "Current range",
        default=WGFMUMeasureCurrentRange.RANGE_100_UA.name,
        choices=[e.name for e in WGFMUMeasureCurrentRange],
    )

    advanced_config = BooleanParameter("Advanced config", default=False)
    plot_points = IntegerParameter("Measure points", default=4000, group_by="advanced_config")

    DATA_COLUMNS = [
        "Top Electrode Voltage",
        "Top Electrode Current",
        "Reversal Voltage",
        "Time",
    ]

    def execute(self):
        seq, reversal_voltages = get_forc_sequence(
            max_voltage=self.max_voltage,
            min_reversal_voltage=self.min_reversal_voltage,
            grid_steps=self.grid_steps,
            pulse_time=self.pulse_time,
            trailing_pulse=True,
        )
        logger.info(
            "FORC family: %d reversal curves from %.3g V to %.3g V, %d waveform segments",
            len(reversal_voltages),
            reversal_voltages[0],
            reversal_voltages[-1],
            len(seq.pulses),
        )

        top_data, _ = run_waveforms(
            b1500=self.b1500,
            top_seq=seq,
            top_ch=self.top,
            bottom_seq=None,
            bottom_ch=None,
            repetitions=1,
            current_range=WGFMUMeasureCurrentRange[self.current_range],
            measure=True,
            plot_points=self.plot_points,
        )
        times, voltages, currents = top_data

        # Tag every sample with its curve's reversal voltage; drop the leading
        # saturation ramp and the trailing settle pulse (labelled NaN).
        labels = split_forc_record(voltages, max_voltage=self.max_voltage, reversal_voltages=reversal_voltages)
        mask = ~np.isnan(labels)
        n_curves = len(np.unique(labels[mask]))
        if n_curves != len(reversal_voltages):
            logger.warning(
                "Detected %d reversal curves in the record but built %d; "
                "check the saturation voltage and measure-point count",
                n_curves,
                len(reversal_voltages),
            )

        self.emit(
            "batch results",
            {
                "Reversal Voltage": labels[mask],
                "Top Electrode Voltage": np.asarray(voltages)[mask],
                "Top Electrode Current": np.asarray(currents)[mask],
                "Time": np.asarray(times)[mask],
            },
        )


class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__(
            procedure_class=WgfmuForcProcedure,
            logger=logger,
        )
        # The natural FORC view is transient current vs applied voltage, with the
        # family of reversal curves overlaid.
        plot = next(w for w in self.widget_list if isinstance(w, BasePlotWidget))
        plot.columns_x.setCurrentText("Top Electrode Voltage")
        plot.columns_y.setCurrentText("Top Electrode Current")


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
