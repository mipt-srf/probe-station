from socket import timeout

from pymeasure.instruments.agilent.agilentB1500 import (
    ADCType,
    AgilentB1500,
    MeasMode,
    MeasOpMode,
    SweepMode,
)
from pyparsing import C


def connect_instrument():
    """Connect to the Agilent B1500 instrument."""
    try:
        b1500 = AgilentB1500("USB1::0x0957::0x0001::0001::0::INSTR", timeout=60000)
        # b1500.reset()
        b1500.initialize_all_smus()
        b1500.data_format(1, mode=1)  # 21 for new, 1 for old (?)

        return b1500
    except Exception:
        raise ConnectionError("Could not connect to the Agilent B1500 instrument.")


def check_all_errors(b1500):
    while True:
        try:
            b1500.check_errors()
        except Exception as e:
            print(e)
        else:
            break


def get_smu_by_number(b1500, smu_number):
    target_name = f"SMU{smu_number}"

    for smu in b1500.smu_references:
        if smu.name == target_name:
            return smu

    raise ValueError(f"SMU{smu_number} not found in smu_references")


def parse_data(string):
    value_strings = string.split(",")
    values = [float(value_str[3:]) for value_str in value_strings]
    return values
