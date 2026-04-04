import datetime
import os
import time

from smu.cycling import cycle
from smu.plot_fig import plot_fig, save_data
from smu.PUND_waveform import create_waveform
from smu.SMU_device import SMUDevice

time.sleep(0)
device = "SMU"
device = "TCPIP0::192.168.81.20::inst0::INSTR"

ifcycle = True
terminal = "rear"

area = 50**2 * 1e-8
save = True
now = datetime.datetime.now()
save_name = f"{now.strftime('%m-%d-%y time-%H %M')}"
dir = os.path.join(os.getcwd(), "2021-03-10", "field7_c5_25um")
print(dir)

"""
params is a dictionary with key parameters for a PUND sweep.

Vf - first voltage
Vs - second voltage
rise - number of measurements during the rise
hold - number of measurements to be done while maintaining the applied voltage
space - number of measurements between pulses
n_cycles - number of PUND cycles

Time required for a single measurement is approximately 0.5 ms. It is the limit for this SMU. The only way to control
rise/hold/space time is to change the number of measurements.
"""

params = {
    "Vf": -3,
    "Vs": 3,
    "rise": 10,
    "hold": 2,
    "space": 15,
    "n_cycles": 4,
    "growth_rate": 5,
}

# connect_pv(ser) 7.2366859912872314


with SMUDevice(device) as smu:
    smu.set_terminal(terminal)
    smu.check_for_errors()

    if ifcycle:
        cycle(smu, 50, params["Vf"], params["Vs"])
        # cycle(smu, 10, params['Vf'], params['Vs'])
    smu.check_for_errors()

    smu.setup_sense_subsystem(compl=1e-4, range=1e-4, int_time=0, counts=1)
    smu.setup_source_subsystem()
    smu.check_for_errors()

    waveform = create_waveform(params, by_rate=False)
    smu.voltage_list_sweep(waveform, params["n_cycles"])

    smu.initiate()
    smu.wait()

    smu.check_for_errors()
    data = smu.get_traces()
    smu.close()

plot_fig(data, params, area, save=save, path=dir, name=save_name)

if save:
    save_data(data, path=dir, name=save_name + ".h5")
