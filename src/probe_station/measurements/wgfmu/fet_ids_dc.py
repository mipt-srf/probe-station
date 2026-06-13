"""WGFMU DC procedure: FET drain/gate current at a fixed DC bias.

Uses the WGFMU DC operation mode (User's Guide section "If You Perform DC
Measurement", Table 3-19) rather than the ALWG waveform path. The gate and
drain WGFMU channels are placed in DC mode, biased with ``WGFMU_dcforceVoltage``,
and read with ``WGFMU_dcmeasureAveragedValue`` for a single averaged current
point each -- the WGFMU analogue of the SMU ``Ids (t)`` single-point read.
"""

import logging

from keysight_b1530a._bindings.errors import get_error_summary
from keysight_b1530a.errors import WGFMUError
from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    ListParameter,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.b1500 import (
    WGFMUMeasureCurrentRange,
    WGFMUMeasureMode,
    WGFMUOperationMode,
)
from probe_station.measurements.b1500_helpers import max_compliance
from probe_station.measurements.pymeasure_base import BaseWindow, run_app
from probe_station.measurements.wgfmu._base import WgfmuProcedure

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class WgfmuFetIdsDcProcedure(WgfmuProcedure):
    """Measure FET drain and gate current at a fixed DC bias on the WGFMU.

    The gate and drain channels are driven with constant DC voltages via the
    WGFMU DC operation mode and each returns a single averaged current reading.
    The two idle terminals -- source and substrate (base) -- are held at 0 V via
    SMU channels for the duration, matching the grounding done by the WGFMU
    ``Ids (Vg)`` procedure (source grounded, Vds on the drain).
    """

    # Parameters are declared in GUI order (see WgfmuProcedure).
    gate = IntegerParameter("Gate channel (WGFMU)", default=2)
    drain = IntegerParameter("Drain channel (WGFMU)", default=1)
    source = IntegerParameter("Source channel (SMU, grounded)", default=1)
    base = IntegerParameter("Base channel (SMU, grounded)", default=2)

    gate_voltage = FloatParameter("Gate voltage", units="V", default=1.0)
    drain_voltage = FloatParameter("Drain voltage", units="V", default=0.25)

    current_range = ListParameter(
        "Current range",
        default=WGFMUMeasureCurrentRange.RANGE_10_MA.name,
        choices=[e.name for e in WGFMUMeasureCurrentRange],
    )

    advanced_config = BooleanParameter("Advanced config", default=False)
    # WGFMU_dcmeasureAveragedValue: sampling interval = interval * 5 ns; both
    # points and interval are bounded to 1..65535 by the instrument.
    average_points = IntegerParameter(
        "Averaging points", default=1000, minimum=1, maximum=65535, group_by="advanced_config"
    )
    sample_interval = IntegerParameter(
        "Sampling interval (x5 ns)", default=20, minimum=1, maximum=65535, group_by="advanced_config"
    )

    DATA_COLUMNS = ["Drain Current", "Gate Current"]

    def execute(self):
        log.info(f"Starting the {self.__class__.__name__}")

        # Hold the idle terminals (source, substrate) at 0 V via SMUs, mirroring
        # the WGFMU Ids(Vg) grounding.
        for channel in (self.source, self.base):
            smu = self.b1500.smus[channel]
            smu.enable()
            smu.force("voltage", 0, 0, max_compliance(smu, 0))

        gate_wgfmu = self.b1500.wgfmus[self.gate]
        drain_wgfmu = self.b1500.wgfmus[self.drain]
        current_range = WGFMUMeasureCurrentRange[self.current_range]

        try:
            for wgfmu in (gate_wgfmu, drain_wgfmu):
                wgfmu.set_operation_mode(WGFMUOperationMode.DC)
                wgfmu.set_measure_mode(WGFMUMeasureMode.CURRENT)
                wgfmu.set_measure_current_range(current_range)
                wgfmu.enable()

            gate_wgfmu.dc_force_voltage(self.gate_voltage)
            drain_wgfmu.dc_force_voltage(self.drain_voltage)

            drain_current = drain_wgfmu.dc_measure_averaged_value(self.average_points, self.sample_interval)
            gate_current = gate_wgfmu.dc_measure_averaged_value(self.average_points, self.sample_interval)

            log.info(f"Drain current: {drain_current:.6e} A, Gate current: {gate_current:.6e} A")

            self.emit("results", {"Drain Current": drain_current, "Gate Current": gate_current})

            # Return both channels to 0 V and release them.
            gate_wgfmu.dc_force_voltage(0)
            drain_wgfmu.dc_force_voltage(0)
            gate_wgfmu.disable()
            drain_wgfmu.disable()
        except WGFMUError:
            log.error(f"{get_error_summary()}")
            self.b1500.clear_wgfmu()
            raise
        except Exception:
            # Any other failure must not leave the FET gate/drain biased;
            # clearing the WGFMU returns the channels to a safe 0 V state.
            log.exception("FET DC measurement failed; clearing WGFMU")
            self.b1500.clear_wgfmu()
            raise


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (LogWidget("Experiment Log"),)
        super().__init__(
            procedure_class=WgfmuFetIdsDcProcedure,
            widget_list=widget_list,
            logger=log,
        )


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
