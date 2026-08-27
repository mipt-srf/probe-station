import numpy as np

from probe_station.measurements.b1500 import B1500, RSUOutputMode
from probe_station.measurements.b1500_helpers import connect_instrument, max_compliance


def run(b1500: B1500, start, end, steps, top=4, bottom=3):
    b1500.rsus[1].set_output(RSUOutputMode.SMU)
    b1500.rsus[2].set_output(RSUOutputMode.SMU)

    voltages_forced = np.linspace(start, end, steps)

    times = np.zeros(steps)
    currents = np.zeros(steps)
    voltages_measured = np.zeros(steps)

    top_smu = b1500.smus[top]
    bottom_smu = b1500.smus[bottom]

    b1500.force_gnd()

    top_smu.enable()
    bottom_smu.enable()

    peak = max(abs(start), abs(end))
    top_smu.force("voltage", 0, 0, max_compliance(top_smu, peak))
    bottom_smu.force("voltage", 0, 0, max_compliance(bottom_smu, 0))

    b1500.clear_timer()

    for i, voltage in enumerate(voltages_forced):
        time, current, voltage = measure_at_voltage(b1500, voltage, top=top, bottom=bottom)
        times[i] = time
        currents[i] = current
        voltages_measured[i] = voltage

    b1500.force_gnd()


# Slot number of the SMU wired to each top channel, as addressed by TTIV.
_TTIV_SLOTS = {1: 4, 2: 6, 3: 7, 4: 8}


def measure_at_voltage(b1500: B1500, voltage, top=4, bottom=3):
    top_smu = b1500.smus[top]
    top_smu.force("voltage", 0, voltage)  # 4 ms between steps, 10 ms with measuring
    # Written and read separately instead of ask(): binary data has no
    # terminator, so the reply is read as a fixed number of values.
    b1500.write(f"TTIV {_TTIV_SLOTS[top]}, 11, 0")
    time, current, voltage_measured = b1500.read_values(3)

    return time, current, voltage_measured


if __name__ == "__main__":
    b1500 = connect_instrument()
    run(b1500, start=-3, end=3, steps=100, top=4)
