import numpy as np
from matplotlib import pyplot as plt
from pymeasure.instruments.agilent.agilentB1500 import (
    MeasMode,
    MFCMUMeasurementMode,
    SCUUPath,
    SweepMode,
)

from probe_station.measurements.b1500 import B1500
from probe_station.measurements.b1500_helpers import check_all_errors, connect_instrument, parse_data
from probe_station.measurements.rsu import RSU, RSUOutputMode, setup_rsu_output

PLOT_POINTS = 100

# ACT auto-mode coefficient range (B1500 Programming Guide, "ACT", page 4-36):
# averaging samples = avg_per_point * initial averaging, with the coefficient
# limited to 1..1023.
MAX_AVG_PER_POINT = 1023


def run(b1500: B1500, first_bias=-3, second_bias=3, avg_per_point=1, plot=False):
    """Run a B1500 CMU CV double sweep.

    :param avg_per_point: Native CMU averaging coefficient (``ACT`` auto mode):
        the A/D converter averages ``avg_per_point * initial averaging`` samples
        at each of the :data:`PLOT_POINTS` sweep points. 1 disables extra
        averaging; higher values trade sweep time for lower capacitance noise.
    """
    if not 1 <= avg_per_point <= MAX_AVG_PER_POINT:
        raise ValueError(f"avg_per_point must be between 1 and {MAX_AVG_PER_POINT}, got {avg_per_point}")
    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)
    cmu = b1500.cmu
    b1500.time_stamp = True
    cmu.set_scuu_path(SCUUPath.CMU)
    cmu.enabled = True
    cmu.set_measurement_mode(MFCMUMeasurementMode.CP_RP)
    cmu.voltage_ac = 0.1
    cmu.frequency_ac = 1e4

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


def get_results(b1500: B1500, plot=False):
    res = b1500.read()
    parsed = parse_data(res)

    # The CMU now averages each point internally (ACT), so every reading is a
    # final point at its own voltage -- no host-side binning.
    _ = np.array(parsed[::6])
    Cp = np.array(parsed[1::6])
    Rp = np.array(parsed[2::6])
    ac = np.array(parsed[3::6])
    dc_measured = np.array(parsed[4::6])
    dc_forced = np.array(parsed[5::6])

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
    run(b1500, plot=True)
    check_all_errors(b1500)
    get_results(b1500, plot=True)
    b1500.close_wgfmu_session()
