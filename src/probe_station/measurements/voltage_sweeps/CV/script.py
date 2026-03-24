import numpy as np
from matplotlib import pyplot as plt
from pymeasure.instruments.agilent.agilentB1500 import (
    MeasMode,
    MFCMUMeasurementMode,
    SCUUPath,
    SweepMode,
)

from probe_station.measurements.b1500 import B1500
from probe_station.measurements.common import (
    RSU,
    RSUOutputMode,
    check_all_errors,
    connect_instrument,
    parse_data,
    setup_rsu_output,
)

PLOT_POINTS = 100
_VALUES_PER_CV_STEP = 6  # status, Cp, Rp, ac, dc_measured, dc_forced


def iter_sweep_results(b1500: B1500, total_steps: int):
    """Read CV sweep data step-by-step as each point completes (B1500 guide section 1-19).

    Uses comma as VISA termination character to read one value at a time from the
    instrument output buffer as the sweep progresses. Call after run() has sent the trigger.

    Yields (Cp, Rp, dc_measured, dc_forced) for each sweep step.
    """
    resource = b1500.adapter.connection
    original_termination = resource.read_termination
    resource.read_termination = ","
    total_values = total_steps * _VALUES_PER_CV_STEP
    try:
        buf = []
        for i in range(total_values):
            if i == total_values - 1:
                resource.read_termination = original_termination
            raw = resource.read().strip()
            buf.append(float(raw[3:]))
            if len(buf) == _VALUES_PER_CV_STEP:
                _, Cp, Rp, _ac, dc_measured, dc_forced = buf
                buf = []
                yield Cp, Rp, dc_measured, dc_forced
    finally:
        resource.read_termination = original_termination


def run(b1500: B1500, first_bias=-3, second_bias=3, avg_per_point=1, plot=False):
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


def get_results(b1500: B1500, plot=False):
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
    run(b1500, plot=True)
    check_all_errors(b1500)
    get_results(b1500, plot=True)
    b1500.close_wgfmu_session()
