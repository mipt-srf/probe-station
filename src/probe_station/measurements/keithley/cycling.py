import time

from smu.SMU_device import SMUDevice


def cycle(smu: SMUDevice, n_times, vf, vs):
    params = {
        "Vf": vf,
        "Vs": vs,
        "n_cycles": n_times,
    }

    waveform = [0, params["Vf"], params["Vf"], 0, 0, params["Vs"], params["Vs"], 0]
    smu.check_for_errors()

    smu.setup_sense_subsystem(int_time=0, compl=1e-4, range=1e-4)
    smu.check_for_errors()

    smu.voltage_list_sweep(waveform, params["n_cycles"])

    smu.initiate()
    smu.check_for_errors()

    smu.wait()


if __name__ == "__main__":
    time.sleep(0)
    instrument_id = "SMU"
    smu = SMUDevice(instrument_id)
    smu.connect()

    smu.set_terminal("front")
    cycle(smu, 10, 1, -1)
