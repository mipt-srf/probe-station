from matplotlib import pyplot as plt

from probe_station.measurements.b1500 import (
    B1500,
    SMU,
    ADCMode,
    ADCType,
    ControlMode,
    MeasMode,
    MeasOpMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
    SweepMode,
)

b1500 = B1500()
b1500.reset()
b1500.data_format(output_format=1, mode=1)

voltage_start = -3
voltage_end = 3
top_channel = 4
bottom_channel = 3
steps = 100
average = 127

b1500.io_control_mode = ControlMode.SMU_PGU_SELECTOR
b1500.set_port_connection(port=PgSelectorPort.OUTPUT_1_FIRST, status=PgSelectorConnectionStatus.SMU_ON)
b1500.set_port_connection(port=PgSelectorPort.OUTPUT_2_FIRST, status=PgSelectorConnectionStatus.SMU_ON)

smu_top: SMU = b1500.smus[top_channel]
smu_top.enable()

smu_bottom: SMU = b1500.smus[bottom_channel]
smu_bottom.enable()

smu_top.force(source_type="voltage", source_range=0, output=0)
smu_bottom.force(source_type="voltage", source_range=0, output=0)

b1500.time_stamp = True
b1500.meas_mode(MeasMode.STAIRCASE_SWEEP, smu_top)
smu_top.meas_op_mode = MeasOpMode.CURRENT
smu_top.meas_range_current = 0
smu_top.adc_type = ADCType.HRADC
b1500.adc_setup(ADCType.HRADC, ADCMode.MANUAL, average)

smu_top.staircase_sweep_source(
    source_type="Voltage",
    mode=SweepMode.LINEAR_DOUBLE,
    source_range=0,
    start=voltage_start,
    stop=voltage_end,
    steps=steps,
    comp=1e-1,
)

b1500.clear_timer()
b1500.send_trigger()

data = b1500.read_data(number_of_points=2 * steps)
b1500.force_gnd()

times = data[f"{smu_top.name} Time (s)"].to_numpy()
currents = data[f"{smu_top.name} Current (A)"].to_numpy()
voltages = data[f"{smu_top.name} Voltage (V)"].to_numpy()

plt.figure()
plt.plot(voltages, abs(currents))
plt.xlabel("Voltage (V)")
plt.ylabel("Current (A)")
plt.yscale("log")
plt.tight_layout()
plt.show()
