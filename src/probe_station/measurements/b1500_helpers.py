"""Helper functions for working with a connected Agilent B1500 instance."""

import logging

from probe_station import B1500

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


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


def parse_data(string):
    """Parse a comma-separated measurement data string into a list of floats.

    :param string: Raw data string from the instrument (e.g. ``"NCI+1.234E-05,NCI+5.678E-06"``).
    :return: List of parsed float values.
    """
    value_strings = string.split(",")
    values = [float(value_str[3:]) for value_str in value_strings]
    return values
