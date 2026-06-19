"""Quasi-static CV (QSCV) measurement runner.

Implements the quasi-static capacitance-voltage measurement from the Keysight
B1500 Programming Guide (Edition 15, "Quasi-static CV Measurements", page 3-61).
One SMU sweeps the gate voltage in a staircase and, at every interior step,
measures the gate capacitance from the charge needed to step the output by
``c_voltage`` (the QSCV measurement voltage); the leakage current is measured
and compensated at the same step. The remaining electrodes (drain, source,
substrate) are held at 0 V.

The QSCV-specific SCPI commands (``MM 13``, ``QSC``, ``QSL``, ``QSM``, ``QSR``,
``QST``, ``QSV``, ``QSZ``) are not wrapped by pymeasure, so they are issued
verbatim here.
"""

import logging

import numpy as np
from matplotlib import pyplot as plt

from probe_station.measurements.b1500 import B1500
from probe_station.measurements.b1500_helpers import connect_instrument, parse_data
from probe_station.measurements.rsu import RSU, RSUOutputMode, setup_rsu_output

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Data blocks returned per sweep step with the time stamp (TSC) and leakage
# current data output (QSL) both enabled, in stream order:
#   time, leakage current, capacitance, source voltage.
VALUES_PER_STEP = 4

# linteg (leakage-current integration) tops out at 2 s / 50 Hz, whereas cinteg
# (capacitance integration) goes up to 400 s. Cap the shared integration time
# at this ceiling so a long capacitance integration cannot push linteg out of
# range and trigger an instrument error.
MAX_LEAK_INTEGRATION = 2.0

# QSR current measurement range code -> fixed full-scale current (A). QSCV has
# no auto-ranging, so this range must cover both the leakage current and the
# capacitance measurement current (roughly C * cvoltage / cinteg). It therefore
# bounds the largest measurable capacitance; too small a range aborts the
# measurement with Error 242. The widest range (-14, 1 uA) caps QSCV at roughly
# 1 uF * cvoltage / cinteg, beyond which the CMU CV sweep is the right tool.
QSR_RANGE_CURRENTS = {
    -9: 10e-12,
    -10: 100e-12,
    -11: 1e-9,
    -12: 10e-9,
    -13: 100e-9,
    -14: 1e-6,
}


def step_count(start, stop, step_voltage):
    """Number of QSCV capacitance measurement points for a single linear sweep.

    Mirrors the guide's formula ``step = |start - stop| / |step_voltage| - 1``.
    The capacitance is measured at every interior sweep step -- i.e. not at the
    start and stop voltages themselves -- so the count is one less than the
    number of voltage intervals.
    """
    steps = round(abs(stop - start) / abs(step_voltage)) - 1
    if steps < 1:
        raise ValueError(
            f"Voltage span of {abs(stop - start)} V with a {abs(step_voltage)} V step "
            "yields no QSCV measurement points; reduce the step voltage or widen the span."
        )
    return steps


def _setup_qscv(
    b1500: B1500,
    *,
    start,
    stop,
    step_voltage=0.1,
    c_voltage=0.1,
    hold=5.0,
    integration_time=0.1,
    delay=0.0,
    current_range=-11,
    current_comp=0.1,
    auto_abort=True,
    offset_cancel=False,
    gate=4,
    drain=1,
    source=3,
    base=2,
):
    """Apply the full QSCV measurement setup, short of triggering it.

    Shared by :func:`run` (the sweep) and :func:`measure_offset` (the
    open-terminal offset calibration) so both run under identical conditions --
    the B1500 requires the measurement setup to be complete before an offset
    measurement, and an offset is only valid for the range it was taken at.

    :param current_range: QSCV current measurement range code (``QSR``), -9 to
        -14: -9=10 pA, -10=100 pA, -11=1 nA, -12=10 nA, -13=100 nA, -14=1 uA.
        Must cover the capacitance measurement current (~C * cvoltage / cinteg);
        too small a range aborts the sweep with Error 242.
    :param auto_abort: Stop the sweep on compliance/AD-overflow/oscillation
        (``QSM 2``). Disable (``QSM 1``) to force a full sweep on a device that
        trips the abort, at the cost of protection against oscillation.
    :param offset_cancel: Enable the stored capacitance offset cancel (``QSZ 1``)
        instead of leaving it off (``QSZ 0``). The offset must have been measured
        first via :func:`measure_offset`.
    :returns: Number of measurement points.
    """
    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    gate_smu = b1500.smus[gate]
    drain_smu = b1500.smus[drain]
    source_smu = b1500.smus[source]
    base_smu = b1500.smus[base]
    for smu in (gate_smu, drain_smu, source_smu, base_smu):
        smu.enable()

    chnum = gate_smu.channel
    steps = step_count(start, stop, step_voltage)
    leak_integration_time = min(integration_time, MAX_LEAK_INTEGRATION)

    range_current = QSR_RANGE_CURRENTS.get(current_range)
    if range_current is not None and c_voltage > 0:
        c_max = range_current * integration_time / c_voltage
        logger.info(
            "QSCV current range %d (%g A) measures capacitance up to ~%.2e F at "
            "cinteg=%g s, cvoltage=%g V. Use a wider range for a larger device.",
            current_range,
            range_current,
            c_max,
            integration_time,
            c_voltage,
        )

    b1500.time_stamp = True  # TSC 1: prepend the time stamp to every step.
    b1500.write(f"MM 13,{chnum}")  # QSCV measurement; the gate channel sweeps and measures.
    b1500.check_errors()
    b1500.write("QSC 0")  # Normal QSCV operation.
    b1500.write("QSL 1,1")  # Leakage current: data output on, compensation on.
    # Auto abort on (2) / off (1); on abort the sweep returns to the start value.
    b1500.write(f"QSM {2 if auto_abort else 1},1")
    b1500.write(f"QSR {current_range}")  # Fixed current measurement range.
    b1500.write(f"QST {integration_time},{leak_integration_time},{hold},{delay}")
    # QSV chnum,mode,vrange,start,stop,cvoltage,step,Icomp -- mode 1 (linear single), auto range.
    b1500.write(f"QSV {chnum},1,0,{start},{stop},{c_voltage},{steps},{current_comp}")
    b1500.check_errors()
    b1500.write(f"QSZ {1 if offset_cancel else 0}")  # Capacitance offset cancel on/off.

    # Hold the non-gate electrodes at 0 V (DV chnum,range,output,comp).
    drain_smu.force("voltage", 0, 0, current_comp)
    source_smu.force("voltage", 0, 0, current_comp)
    base_smu.force("voltage", 0, 0, current_comp)

    return steps


def run(b1500: B1500, *, offset_cancel=False, **setup):
    """Configure and trigger a single-stair quasi-static CV sweep on the gate.

    Accepts the same keyword arguments as :func:`_setup_qscv` (``start`` and
    ``stop`` are required).

    :returns: Number of measurement points; read ``count * VALUES_PER_STEP``
        values via :meth:`B1500.iter_output`.
    """
    steps = _setup_qscv(b1500, offset_cancel=offset_cancel, **setup)
    b1500.clear_timer()  # TSR: reset the time stamp just before the trigger.
    b1500.send_trigger()  # XE: start the measurement.
    return steps


def measure_offset(b1500: B1500, **setup):
    """Measure the open-terminal capacitance offset and enable offset cancel.

    Run this with the device terminals **open** (probe tips lifted). It applies
    the same QSCV setup as the sweep (pass the matching keyword arguments,
    crucially the same ``current_range``), performs the offset measurement
    (``QSZ 2``), enables the offset cancel (``QSZ 1``), and returns the offset
    in farads. The offset is stored in the instrument and subtracted from every
    later sweep run with ``offset_cancel=True``, until it is re-measured or the
    instrument is reset.

    :returns: The measured open-terminal capacitance offset, in farads.
    """
    _setup_qscv(b1500, offset_cancel=False, **setup)  # QSZ 0 while measuring the offset.
    b1500.write("QSZ 2")  # Trigger the open-terminal offset measurement.
    b1500.ask("*OPC?")  # Wait for completion; consumes the "1" reply before the data.
    offset = parse_data(b1500.read())[-1]  # Single capacitance value, in F.
    b1500.write("QSZ 1")  # Enable offset cancel for subsequent sweeps.
    b1500.check_errors()
    logger.info("Open-terminal capacitance offset: %.4e F (%.3f pF); offset cancel enabled.", offset, offset * 1e12)
    return offset


def get_results(b1500: B1500, steps, plot=False):
    """Read a completed QSCV sweep as ``(voltage, capacitance, leakage, time)`` arrays."""
    times, leakages, caps, voltages = (np.array(col) for col in zip(*b1500.iter_output(steps, VALUES_PER_STEP)))

    if plot:
        fig, ax1 = plt.subplots()

        color = "tab:blue"
        ax1.set_xlabel("Voltage (V)")
        ax1.set_ylabel("Capacitance (F)", color=color)
        ax1.plot(voltages, caps, color=color)
        ax1.tick_params(axis="y", labelcolor=color)

        ax2 = ax1.twinx()
        color = "tab:red"
        ax2.set_ylabel("Leakage current (A)", color=color)
        ax2.plot(voltages, np.abs(leakages), color=color)
        ax2.set_yscale("log")
        ax2.tick_params(axis="y", labelcolor=color)

        fig.tight_layout()
        plt.show()

    return voltages, caps, leakages, times


if __name__ == "__main__":
    b1500 = connect_instrument(reset=True)
    steps = run(b1500, start=-3, stop=3)
    voltages, caps, leakages, times = get_results(b1500, steps, plot=True)
    b1500.force_gnd()
    b1500.close_wgfmu_session()
