import pyvisa
from matplotlib import pyplot as plt

rm = pyvisa.ResourceManager()
b1500 = rm.open_resource(
    "USB1::0x0957::0x0001::0001::0::INSTR",
    read_termination="\r\n",
    write_termination="\r\n",
)
b1500.timeout = 600_000
b1500.write("*RST")
b1500.write("FMT 1, 1")

voltage_start = -3
voltage_end = 3
top_channel = 8
bottom_channel = 7
steps = 100
average = 127

b1500.write("ERMOD 1")
b1500.write("ERSSP 0, 1")
b1500.write("ERSSP 1, 1")

b1500.write(f"CN {top_channel}")
b1500.write(f"CN {bottom_channel}")

b1500.write(f"DV {top_channel}, 0, 0")
b1500.write(f"DV {bottom_channel}, 0, 0")

b1500.write("TSC 1")
b1500.write("AV 10, 0")
b1500.write(f"MM 2, {top_channel}")
b1500.write(f"CMM {top_channel}, 1")
b1500.write(f"RI {top_channel}, 0")
b1500.write(f"AAD {top_channel}, 1")
b1500.write(f"AIT 1, 1, {average}")

b1500.write(f"WV {top_channel}, 3, 0, {voltage_start}, {voltage_end}, {steps}, 0.1")

b1500.write("TSR")
b1500.write("XE")

tokens = b1500.read().split(",")
b1500.write("DZ")

values = [float(token[3:]) for token in tokens]
times = values[0::3]
currents = values[1::3]
voltages = values[2::3]

plt.figure()
plt.plot(voltages, [abs(current) for current in currents])
plt.xlabel("Voltage (V)")
plt.ylabel("Current (A)")
plt.yscale("log")
plt.tight_layout()
plt.show()
