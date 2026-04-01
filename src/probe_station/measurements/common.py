"""Common utilities for instrument connection and RSU/SMU configuration."""

import logging
from datetime import datetime
from enum import Enum
from pathlib import Path

from keysight_b1530a._bindings.config import WGFMUChannel
from keysight_b1530a._bindings.configuration import set_operation_mode
from keysight_b1530a.enums import WGFMUOperationMode
from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import Metadata, Procedure
from pymeasure.instruments.agilent.agilentB1500 import (
    AgilentB1500,
    ControlMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
)

from probe_station import B1500
from probe_station.utilities import add_file_log_dir

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class BaseProcedure(Procedure):
    """Base class for all probe-station procedures.

    Adds a ``start_time`` metadata field that is automatically recorded in
    the CSV header when a measurement begins.
    """

    start_time = Metadata("Start time", default=0)

    def startup(self):
        super().startup()
        self.start_time = datetime.now()


def take_screenshot(window, dest: str | Path, full_screen: bool = False) -> Path | None:
    """Capture a screenshot and save it to *dest*.

    :param window: The Qt widget to capture (ignored when *full_screen* is ``True``).
    :param dest: Full path (including filename) for the saved PNG.
    :param full_screen: If ``True``, capture the entire screen instead of *window*.
    :returns: Resolved path to the saved file, or ``None`` on failure.
    """
    from qtpy.QtWidgets import QApplication

    dest = Path(dest)
    try:
        if full_screen:
            pixmap = QApplication.instance().primaryScreen().grabWindow(0)
        else:
            pixmap = window.grab()
        if not pixmap.save(str(dest), "PNG"):
            log.warning("Screenshot failed: could not save to %s", dest)
            return None
        log.info("Screenshot saved: %s", dest)
        return dest
    except Exception as e:
        log.warning("Screenshot failed: %s", e)
        return None


class BaseWindow(ManagedWindowBase):
    """Base class for all probe-station measurement windows.

    ``inputs`` and ``displays`` default to all parameters declared on
    ``procedure_class`` (in definition order).  Pass explicit lists to override.

    ``widget_list`` defaults to ``(PlotWidget("Results Graph", DATA_COLUMNS),
    LogWidget("Experiment Log"))`` when the procedure defines non-empty
    ``DATA_COLUMNS``, otherwise ``(LogWidget("Experiment Log"),)``.

    An optional ``logger`` is connected to the window's log level and the
    ``LogWidget`` found in ``widget_list`` (looked up by type, not by index).

    ``store_measurement`` defaults to ``False``.  Set it to ``True`` on a
    subclass or after construction to enable data storage.

    When data storage is enabled (``store_measurement`` is ``True``), logs are
    written to a ``logs/`` subdirectory of the results directory and a screenshot
    is saved next to the results file when the measurement finishes.
    """

    store_measurement = False

    def __init__(self, *args, procedure_class, widget_list=None, inputs=None, displays=None, logger=None, **kwargs):
        if widget_list is None:
            columns = getattr(procedure_class, "DATA_COLUMNS", [])
            if columns:
                widget_list = (
                    PlotWidget("Results Graph", columns),
                    LogWidget("Experiment Log"),
                )
            else:
                widget_list = (LogWidget("Experiment Log"),)

        if inputs is None:
            inputs = list(procedure_class._parameters.keys())
        if displays is None:
            displays = inputs

        super().__init__(
            *args, procedure_class=procedure_class, widget_list=widget_list, inputs=inputs, displays=displays, **kwargs
        )

        log_widget = next((w for w in widget_list if isinstance(w, LogWidget)), None)
        if log_widget is not None:
            log_widget.handler.setLevel(logging.INFO)
            logging.getLogger().addHandler(log_widget.handler)
        if logger is not None:
            logger.setLevel(self.log_level)
            logger.info("ManagedWindow connected to logging")

        self.setWindowTitle(self.procedure_class.__name__)

    def _queue(self, checked):
        if self.store_measurement:
            add_file_log_dir(Path(self.directory) / "logs")
        super()._queue(checked)

    def finished(self, experiment):
        super().finished(experiment)
        if not self.store_measurement:
            return
        procedure = experiment.procedure
        dest = Path(self.directory) / f"{procedure.start_time:%Y%m%d_%H%M%S}_screenshot.png"
        take_screenshot(self, dest)


class RSUOutputMode(Enum):
    """Output routing mode of the Remote-Sense and Switch Unit (RSU)."""

    SMU = 0
    SPGU = 1
    WGFMU = 2


class RSU(Enum):
    """Identifier for the RSU unit (RSU1 or RSU2)."""

    RSU1 = 1
    RSU2 = 2


def setup_rsu_output(b1500: AgilentB1500, rsu: RSU = RSU.RSU2, mode: RSUOutputMode = RSUOutputMode.SMU):
    """Configure the RSU output routing for the specified mode.

    :param b1500: Connected ``AgilentB1500`` instance.
    :param rsu: Which RSU to configure.
    :param mode: Desired output mode (SMU, SPGU, or WGFMU).
    """
    if not b1500.io_control_mode == ControlMode.SMU_PGU_SELECTOR:
        b1500.io_control_mode = ControlMode.SMU_PGU_SELECTOR
    if rsu == RSU.RSU1:
        if mode == RSUOutputMode.SMU:
            b1500.set_port_connection(port=PgSelectorPort.OUTPUT_1_FIRST, status=PgSelectorConnectionStatus.SMU_ON)
            set_operation_mode(mode=WGFMUOperationMode.SMU, channel=WGFMUChannel.CH2)
        if mode == RSUOutputMode.SPGU:
            b1500.set_port_connection(port=PgSelectorPort.OUTPUT_1_FIRST, status=PgSelectorConnectionStatus.PGU_ON)
            set_operation_mode(mode=WGFMUOperationMode.SMU, channel=WGFMUChannel.CH2)
        if mode == RSUOutputMode.WGFMU:
            set_operation_mode(mode=WGFMUOperationMode.FASTIV, channel=WGFMUChannel.CH2)
    elif rsu == RSU.RSU2:
        if mode == RSUOutputMode.SMU:
            b1500.set_port_connection(port=PgSelectorPort.OUTPUT_2_FIRST, status=PgSelectorConnectionStatus.SMU_ON)
            set_operation_mode(mode=WGFMUOperationMode.SMU, channel=WGFMUChannel.CH1)
        if mode == RSUOutputMode.SPGU:
            b1500.set_port_connection(port=PgSelectorPort.OUTPUT_2_FIRST, status=PgSelectorConnectionStatus.PGU_ON)
            set_operation_mode(mode=WGFMUOperationMode.SMU, channel=WGFMUChannel.CH1)
        if mode == RSUOutputMode.WGFMU:
            set_operation_mode(mode=WGFMUOperationMode.FASTIV, channel=WGFMUChannel.CH1)


_COMPLIANCE_THRESHOLDS = {
    "HRSMU": [(20, 100e-3), (40, 50e-3), (100, 20e-3)],
    "MPSMU": [(20, 100e-3), (40, 50e-3), (100, 20e-3)],
    "HPSMU": [(20, 1.0), (40, 500e-3), (100, 125e-3), (200, 50e-3)],
    "HVSMU": [(1500, 8e-3), (3000, 4e-3)],
}


def max_compliance(smu, peak_voltage: float) -> float:
    """Return the maximum current compliance in amperes for the given SMU
    and peak output voltage.

    Looks up the hardware limit from Table 4-7 / 4-12 of the B1500
    Programmer's Guide.  Use ``max(abs(start), abs(end))`` for sweeps and
    ``abs(voltage)`` for DC measurements as ``peak_voltage``.

    :param smu: SMU object with a ``.type`` string attribute
        (e.g. ``"HRSMU"``, ``"MPSMU"``, ``"HPSMU"``, ``"HVSMU"``).
    :param peak_voltage: Maximum absolute output voltage in V.
    :raises ValueError: If the voltage exceeds the SMU's range or the
        SMU type is not supported.
    """
    peak_voltage = abs(peak_voltage)
    thresholds = _COMPLIANCE_THRESHOLDS.get(smu.type)
    if thresholds is None:
        raise ValueError(f"SMU type {smu.type!r} is not supported by max_compliance")
    for ceiling, compliance in thresholds:
        if peak_voltage <= ceiling:
            return compliance
    raise ValueError(f"Peak voltage {peak_voltage} V exceeds the maximum for {smu.type} ({thresholds[-1][0]} V)")


def set_smu_compliances(b1500, current_comp=0.1):
    """Enable all SMUs and set a uniform current compliance.

    :param b1500: Connected ``AgilentB1500`` instance.
    :param current_comp: Current compliance value in amperes.
    """
    for smu in b1500.smu_references:
        smu.enable()
        smu.force("Voltage", 0, 0, current_comp)


def enable_all_smus(b1500):
    """Enable every SMU channel on the instrument.

    :param b1500: Connected ``AgilentB1500`` instance.
    """
    for smu in b1500.smu_references:
        smu.enable()


def connect_instrument(timeout=60000, reset=False):
    """Connect to the Agilent B1500 instrument."""
    try:
        b1500 = B1500(timeout=timeout)
        log.info("Connected to Agilent B1500")
        if reset:
            b1500.reset()
            log.info("Agilent B1500 is reset")
        b1500.data_format(1, mode=1)  # 21 for new, 1 for old (?)

        return b1500
    except Exception:
        raise ConnectionError("Could not connect to the Agilent B1500 instrument.")


def check_all_errors(b1500):
    """Query and print all pending instrument errors until the queue is empty.

    :param b1500: Connected ``AgilentB1500`` instance.
    """
    while True:
        try:
            b1500.check_errors()
        except Exception as e:
            log.warning("Instrument error: %s", e)
        else:
            break


def get_smu_by_number(b1500, smu_number):
    """Return the SMU reference matching the given channel number.

    :param b1500: Connected ``AgilentB1500`` instance.
    :param smu_number: Channel number (e.g. 1, 2, 3, 4).
    :return: The matching SMU object.
    :raises ValueError: If the SMU is not found.
    """
    target_name = f"SMU{smu_number}"

    for smu in b1500.smu_references:
        if smu.name == target_name:
            return smu

    raise ValueError(f"SMU{smu_number} not found in smu_references")


def parse_data(string):
    """Parse a comma-separated measurement data string into a list of floats.

    :param string: Raw data string from the instrument (e.g. ``"NCI+1.234E-05,NCI+5.678E-06"``).
    :return: List of parsed float values.
    """
    value_strings = string.split(",")
    values = [float(value_str[3:]) for value_str in value_strings]
    return values
