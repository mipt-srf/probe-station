import numpy as np
from keysight_b1530a._bindings.initialization import close_session, open_session
from matplotlib import pyplot as plt
from pymeasure.instruments.agilent.agilentB1500 import (
    AgilentB1500,
    MeasMode,
    MFCMUMeasurementMode,
    SCUUPath,
    SweepMode,
)

from probe_station.measurements.common import (
    RSU,
    RSUOutputMode,
    check_all_errors,
    connect_instrument,
    parse_data,
    setup_rsu_output,
)

PLOT_POINTS = 100


def run(b1500: AgilentB1500, first_bias=-3, second_bias=3, avg_per_point=1, plot=False):
    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)
    cmu = b1500.cmu
    b1500.time_stamp = True
    cmu.set_scuu_path(SCUUPath.CMU)
    cmu.enabled = True
    cmu.set_measurement_mode(MFCMUMeasurementMode.CP_RP)
    cmu.voltage_ac = 0.1
    cmu.frequency_ac = 1e4

    measure_points = PLOT_POINTS * avg_per_point
    cmu.set_cv_timings(hold_time=0, delay_time=0)
    cmu.set_cv_parameters(mode=SweepMode.LINEAR_DOUBLE, start=first_bias, stop=second_bias, steps=measure_points)

    b1500.write("LMN 1")  # enable monitor, doesn't work
    b1500.meas_mode(MeasMode.CV_SWEEP, cmu)
    b1500.clear_timer()
    b1500.send_trigger()

    cmu.force_dc_bias(0)


def get_results(b1500: AgilentB1500, plot=False):
    res = b1500.read()
    parsed = parse_data(res)

    _ = np.array(parsed[::6])
    Cp = np.array(parsed[1::6])
    Rp = np.array(parsed[2::6])
    ac = np.array(parsed[3::6])
    dc_measured = np.array(parsed[4::6])
    dc_forced = np.array(parsed[5::6])
    measure_points = int(len(Cp) / 2)  # forward and backward

    Cp = np.mean(Cp.reshape(-1, measure_points // PLOT_POINTS), axis=1)
    Rp = np.mean(Rp.reshape(-1, measure_points // PLOT_POINTS), axis=1)
    dc_forced = np.mean(dc_forced.reshape(-1, measure_points // PLOT_POINTS), axis=1)
    dc_measured = np.mean(dc_measured.reshape(-1, measure_points // PLOT_POINTS), axis=1)

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
    open_session()
    run(b1500, plot=True)
    check_all_errors(b1500)
    get_results(b1500, plot=True)
    close_session()
