"""Common utilities for instrument connection and RSU/SMU configuration."""

import logging
from enum import Enum

from keysight_b1530a._bindings.config import WGFMUChannel
from keysight_b1530a._bindings.configuration import set_operation_mode
from keysight_b1530a.enums import WGFMUOperationMode
from pymeasure.instruments.agilent.agilentB1500 import (
    AgilentB1500,
    ControlMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


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


def set_smu_compliances(b1500, current_comp=0.1):
    """Enable all SMUs and set a uniform current compliance.

    :param b1500: Connected ``AgilentB1500`` instance.
    :param current_comp: Current compliance value in amperes.
    """
    for smu in b1500.smu_references:
        smu.enable()
        smu.force("Voltage", 0, 0, 1e-1)


def enable_all_smus(b1500):
    """Enable every SMU channel on the instrument.

    :param b1500: Connected ``AgilentB1500`` instance.
    """
    for smu in b1500.smu_references:
        smu.enable()


def connect_instrument(timeout=60000, reset=False):
    """Connect to the Agilent B1500 instrument."""
    try:
        b1500 = AgilentB1500("USB1::0x0957::0x0001::0001::0::INSTR", timeout=timeout)
        log.info("Connected to Agilent B1500")
        if reset:
            b1500.reset()
            log.info("Agilent B1500 is reset")
        b1500.initialize_all_smus()
        b1500.initialize_all_spgus()
        b1500.initialize_cmu()
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
            print(e)
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
