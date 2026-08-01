import numpy as np
from matplotlib import pyplot as plt

from probe_station.measurements.b1500 import (
    B1500,
    MeasMode,
    MFCMUMeasurementMode,
    RSUOutputMode,
    SCUUPath,
    SweepMode,
)
from probe_station.measurements.b1500_helpers import check_all_errors, connect_instrument, to_cp_rp

PLOT_POINTS = 100

# ACT auto-mode coefficient range (B1500 Programming Guide, "ACT", page 4-36):
# averaging samples = avg_per_point * initial averaging, with the coefficient
# limited to 1..1023.
MAX_AVG_PER_POINT = 1023


def run(b1500: B1500, first_bias=-3, second_bias=3, avg_per_point=1, ac_voltage=0.1, frequency=1e4, plot=False):
    """Run a B1500 CMU CV double sweep.

    :param avg_per_point: Native CMU averaging coefficient (``ACT`` auto mode):
        the A/D converter averages ``avg_per_point * initial averaging`` samples
        at each of the :data:`PLOT_POINTS` sweep points. 1 disables extra
        averaging; higher values trade sweep time for lower capacitance noise.
    :param ac_voltage: CMU AC oscillator level (RMS) in V applied during the
        capacitance measurement.
    :param frequency: CMU AC oscillator frequency in Hz.
    """
    if not 1 <= avg_per_point <= MAX_AVG_PER_POINT:
        raise ValueError(f"avg_per_point must be between 1 and {MAX_AVG_PER_POINT}, got {avg_per_point}")
    b1500.rsu1.set_output(RSUOutputMode.SMU)
    b1500.rsu2.set_output(RSUOutputMode.SMU)
    cmu = b1500.cmu
    b1500.time_stamp = True
    cmu.set_scuu_path(SCUUPath.CMU)
    cmu.enabled = True
    cmu.set_measurement_mode(MFCMUMeasurementMode.CP_RP)
    cmu.voltage_ac = ac_voltage
    cmu.frequency_ac = frequency

    # ACT 0,N: auto averaging mode, N samples per point measured and averaged by
    # the CMU itself, so every emitted point is one true reading at its voltage.
    b1500.write(f"ACT 0,{avg_per_point}")
    cmu.set_cv_timings(hold_time=0, delay_time=0)
    cmu.set_cv_parameters(mode=SweepMode.LINEAR_DOUBLE, start=first_bias, stop=second_bias, steps=PLOT_POINTS)

    b1500.write("LMN 1")  # enable monitor, doesn't work
    b1500.meas_mode(MeasMode.CV_SWEEP, cmu)
    b1500.clear_timer()
    b1500.send_trigger()

    cmu.force_dc_bias(0)
    cmu.voltage_ac = 0


def get_results(b1500: B1500, frequency=1e4, plot=False):
    """Read a completed CV sweep as ``(Cp, Rp, ac, dc_measured, dc_forced)`` arrays.

    :param frequency: The CMU oscillator frequency the sweep was run with,
        needed to convert the impedance pair the binary data format returns
        into Cp/Rp (see :func:`to_cp_rp`).
    """
    records = b1500.read_all_records()

    # The CMU now averages each point internally (ACT), so every reading is a
    # final point at its own voltage -- no host-side binning.
    # Per point, the 6 values are: time, the impedance pair, AC level, measured
    # DC bias and forced DC bias.
    pairs = [to_cp_rp(records[i + 1 : i + 3], frequency) for i in range(0, len(records), 6)]
    Cp, Rp = (np.array(column) for column in zip(*pairs))
    values = [value for *_, value in records]
    ac = np.array(values[3::6])
    dc_measured = np.array(values[4::6])
    dc_forced = np.array(values[5::6])

    if plot:
        fig, ax1 = plt.subplots()

        color = "tab:blue"
        ax1.set_xlabel("Voltage (V)")
        ax1.set_ylabel("Capacitance (F)", color=color)
        ax1.plot(dc_forced, Cp, label="Cp", color=color)
        ax1.tick_params(axis="y", labelcolor=color)

        ax2 = ax1.twinx()
        color = "tab:red"
        ax2.set_ylabel("Resistance (Ω)", color=color)
        ax2.plot(dc_forced, Rp, label="Rp", color=color)
        ax2.tick_params(axis="y", labelcolor=color)

        fig.tight_layout()
        plt.show()

    return Cp, Rp, ac, dc_measured, dc_forced


if __name__ == "__main__":
    b1500 = connect_instrument(reset=True)
    frequency = 1e4
    run(b1500, frequency=frequency, plot=True)
    check_all_errors(b1500)
    get_results(b1500, frequency=frequency, plot=True)
    b1500.close_wgfmu_session()
