import numpy as np
from matplotlib import pyplot as plt
from pymeasure.instruments.agilent.agilentB1500 import (
    AgilentB1500,
    ControlMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
)

from probe_station.measurements.common import check_all_errors, connect_instrument, parse_data

PLOT_POINTS = 100


def run(b1500: AgilentB1500, first_bias=-3, second_bias=3, avg_per_point=1, plot=False):
    b1500.control_mode = ControlMode.SMU_PGU_SELECTOR
    b1500.set_port_connection(port=PgSelectorPort.OUTPUT_2_FIRST, status=PgSelectorConnectionStatus.SMU_ON)
    b1500.set_port_connection(port=PgSelectorPort.OUTPUT_1_FIRST, status=PgSelectorConnectionStatus.SMU_ON)
    i = 901
    b1500.write(f"CN {i}")
    b1500.write("IMP 103")  # Cp-Rp measurement
    b1500.write(f"ACV {i},0.1")  # amplitude (0.25 max)
    b1500.write(f"FC {i},1e4")  # freq

    measure_points = PLOT_POINTS * avg_per_point
    b1500.write(f"WTDCV 0,0")  # hold, delay time
    b1500.write(f"WDCV {i},3,{first_bias},{second_bias},{measure_points}")  # sweep settings (0 to 1, 10 steps)

    b1500.write("LMN 1")  # enable monitor, doesn't work

    b1500.write(f"MM 18,{i}")
    b1500.write("XE")

    b1500.force_gnd()


def get_results(b1500: AgilentB1500, plot=False):
    res = b1500.read()
    parsed = parse_data(res)

    Cp = np.array(parsed[::5])
    Rp = np.array(parsed[1::5])
    ac = np.array(parsed[2::5])
    dc_measured = np.array(parsed[3::5])
    dc_forced = np.array(parsed[4::5])
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
    b1500 = connect_instrument()
    run(b1500, plot=True)
    check_all_errors(b1500)
    get_results(b1500, plot=True)
