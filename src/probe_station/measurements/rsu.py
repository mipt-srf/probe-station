"""Remote-Sense and Switch Unit (RSU) routing configuration."""

from enum import Enum

from keysight_b1530a._bindings.config import WGFMUChannel
from keysight_b1530a._bindings.configuration import set_operation_mode
from keysight_b1530a.enums import WGFMUOperationMode
from pymeasure.instruments.agilent.agilentB1500 import AgilentB1500

from probe_station.measurements.b1500 import (
    ControlMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
)


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
