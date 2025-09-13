import numpy as np
from pymeasure.instruments.agilent.agilentB1500 import (
    AgilentB1500,
    ControlMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
)

from probe_station.measurements.common import connect_instrument, get_smu_by_number, parse_data


def run(b1500: AgilentB1500, start, end, steps, top=4, bottom=3):
    b1500.control_mode = ControlMode.SMU_PGU_SELECTOR
    b1500.set_port_connection(port=PgSelectorPort.OUTPUT_2_FIRST, status=PgSelectorConnectionStatus.SMU_ON)
    b1500.set_port_connection(port=PgSelectorPort.OUTPUT_1_FIRST, status=PgSelectorConnectionStatus.SMU_ON)

    voltages_forced = np.linspace(start, end, steps)

    times = np.zeros(steps)
    currents = np.zeros(steps)
    voltages_measured = np.zeros(steps)

    top_smu = get_smu_by_number(b1500, top)
    bottom_smu = get_smu_by_number(b1500, bottom)

    b1500.force_gnd()

    top_smu.enable()
    bottom_smu.enable()

    b1500.clear_timer()

    for i, voltage in enumerate(voltages_forced):
        time, current, voltage = measure_at_voltage(b1500, voltage, top=top, bottom=bottom)
        times[i] = time
        currents[i] = current
        voltages_measured[i] = voltage

    b1500.force_gnd()


def measure_at_voltage(b1500: AgilentB1500, voltage, top=4, bottom=3):
    top_smu = get_smu_by_number(b1500, top)
    top_smu.force("voltage", 0, voltage)  # 4 ms between steps, 10 ms with measuring
    if top == 4:
        time, current, voltage_measured = parse_data(b1500.ask("TTIV 8, 11, 0"))
    elif top == 3:
        time, current, voltage_measured = parse_data(b1500.ask("TTIV 7, 11,0 "))
    else:
        raise ValueError("Top electrode must be 3 or 4 (for now)")

    return time, current, voltage_measured


if __name__ == "__main__":
    b1500 = connect_instrument()
    run(b1500, start=-3, end=3, steps=100, top=4)
