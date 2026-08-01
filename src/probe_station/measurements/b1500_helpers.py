"""Helper functions for working with a connected Agilent B1500 instance."""

import logging
from math import nan, pi

from probe_station import B1500

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


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


def connect_instrument(timeout=60000, reset=False, data_format=1, mode=1):
    """Connect to the Agilent B1500 instrument.

    :param timeout: VISA timeout in milliseconds.
    :param reset: Whether to reset the instrument after connecting.
    :param data_format: Measurement data output format (``FMT``). 1, 11 and 21
        are ASCII; 14 is the 8 byte binary format, which transfers faster and
        with a higher resolution. All reading paths
        (:meth:`B1500.iter_output`, :meth:`B1500.read_all_values`,
        :meth:`B1500.read_values`) decode whichever format is set here.

        Note that ``IMP`` (:meth:`CMU.set_measurement_mode`) is not effective
        under format 14: the MFCMU then always returns resistance/reactance or
        conductance/susceptance instead of the requested pair.
    :param mode: Data output mode; 1 also returns the source data.
    """
    try:
        b1500 = B1500(timeout=timeout)
        logger.info("Connected to Agilent B1500")
        if reset:
            b1500.reset()
            logger.info("Agilent B1500 is reset")
        # Called after the units are initialized, so the channel names are known.
        b1500.data_format(data_format, mode=mode)

        return b1500
    except Exception as e:
        raise ConnectionError("Could not connect to the Agilent B1500 instrument.") from e


def check_all_errors(b1500):
    """Query and print all pending instrument errors until the queue is empty.

    :param b1500: Connected ``AgilentB1500`` instance.
    """
    while True:
        try:
            b1500.check_errors()
        except Exception as e:  # noqa: BLE001 - any query failure means the error queue is drained
            logger.warning("Instrument error: %s", e)
        else:
            break


def to_cp_rp(records, frequency):
    """Convert an MFCMU impedance or admittance pair into parallel Cp and Rp.

    The ``IMP`` command is not effective for the binary data format 14, so the
    MFCMU reports resistance/reactance or conductance/susceptance whatever
    measurement mode was requested. This maps either pair onto the parallel
    model (``Y = 1/Rp + j*w*Cp``) so that measurements keep reporting Cp/Rp
    independently of the data format in use.

    :param records: The two ``(status, channel, data_name, value)`` records of
        one measurement point, as returned by :meth:`B1500.iter_records`.
    :param frequency: MFCMU oscillator frequency in Hz.
    :return: ``(Cp, Rp)`` in F and Ohm. Values the instrument could not measure
        (``NaN``) and singular conversions propagate as ``NaN``.
    """
    (_, _, first_name, first), (_, _, second_name, second) = records
    if first_name.startswith("Resistance") and second_name.startswith("Reactance"):
        # Y = 1/Z, with Z = R + jX.
        z_squared = first**2 + second**2
        conductance, susceptance = (first / z_squared, -second / z_squared) if z_squared else (nan, nan)
    elif first_name.startswith("Conductance") and second_name.startswith("Susceptance"):
        conductance, susceptance = first, second
    else:
        # Any other pair is already the requested measurement mode (ASCII formats).
        return first, second
    return (susceptance / (2 * pi * frequency), (1 / conductance) if conductance else nan)
