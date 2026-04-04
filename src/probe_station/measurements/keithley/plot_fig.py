import json
import os

import matplotlib.pyplot as plt
import numpy as np


def plot_average(data, params, area, save=False, path=None, name=None):
    plt.figure(figsize=(12, 9))
    voltage = np.array(data["source"])
    current = np.array(data["reading"])
    meas_time = np.array(data["time"])
    try:
        voltages = np.split(voltage, params["n_cycles"])
        currents = np.split(current, params["n_cycles"])
    except ValueError:
        voltages = []
        currents = []
    dt = np.mean(np.diff(np.array(data["time"])))
    c = np.mean(currents, axis=0)
    v = voltages[0]

    logic = np.where(v > 0.025)

    try:
        pv, uv = np.split(v[logic], 2)
        pc, uc = np.split(c[logic], 2)
    except ValueError:
        pass
    try:
        logic = np.where(v < -0.025)
        nv, dv = np.split(v[logic], 2)
        nc, dc = np.split(c[logic], 2)
    except ValueError:
        pass

    charge = np.append(pc, nc) - np.append(uc, dc)
    v_charge = np.append(pv, nv)

    ax = plt.subplot2grid((2, 2), (0, 0), colspan=2, rowspan=1)
    ax3 = plt.subplot2grid((2, 2), (1, 0), colspan=1, rowspan=1)
    ax4 = plt.subplot2grid((2, 2), (1, 1), colspan=1, rowspan=1)

    ax.plot(meas_time[: len(v)], v, linewidth=2, color="teal")

    for spine in ["left", "right", "top", "bottom"]:
        ax.spines[spine].set_linewidth(2)

    for label in ax.get_yticklabels() + ax.get_xticklabels():
        label.set_fontsize(20)
    ax.set_xlabel("Time, s", fontsize=20, labelpad=10)
    ax.set_ylabel("Voltage, V", fontsize=20, labelpad=10)
    ax2 = ax.twinx()
    ax2.locator_params(axis="y", nbins=7)
    ax2.plot(meas_time[: len(v)], c, linewidth=2, color="tomato")
    for label in ax2.get_yticklabels():
        label.set_fontsize(20)
    ax2.set_ylabel(r"Current, $\mu$A", fontsize=20, labelpad=30, rotation=270)

    ax3.plot(v, c * 1e6, linewidth=2, color="tomato")
    for spine in ["left", "right", "top", "bottom"]:
        ax3.spines[spine].set_linewidth(2)

    for label in ax3.get_yticklabels() + ax3.get_xticklabels():
        label.set_fontsize(20)

    ax3.locator_params(axis="y", nbins=7)
    ax3.set_xlabel("Voltage, V", fontsize=20, labelpad=10)
    ax3.set_ylabel(r"Current, $\mu$A", fontsize=20, labelpad=10)
    charge = np.cumsum(charge)
    ax4.plot(v_charge, charge * 1e6 * dt / area, linewidth=2, color="tomato")

    for spine in ["left", "right", "top", "bottom"]:
        ax4.spines[spine].set_linewidth(2)

    for label in ax4.get_yticklabels() + ax4.get_xticklabels():
        label.set_fontsize(20)

    ax4.set_xlabel("Voltage, V", fontsize=20, labelpad=10)
    ax4.set_ylabel(r"2P, uC/cm$^2$", fontsize=20, labelpad=5)

    plt.tight_layout()
    if save:
        try:
            plt.savefig(os.path.join(path, name), dpi=300)
        except FileNotFoundError:
            os.makedirs(path)
            plt.savefig(os.path.join(path, name), dpi=300)
    plt.show()


def plot_fig(data, params, area, save=False, path=None, name=None):
    plt.figure(figsize=(12, 9))
    voltage = np.array(data["source"])
    current = np.array(data["reading"])
    meas_time = np.array(data["time"])

    try:
        voltages = np.split(voltage, params["n_cycles"])
        currents = np.split(current, params["n_cycles"])
    except ValueError:
        voltages = []
        currents = []
    dt = np.mean(np.diff(np.array(data["time"])))

    v_charge = np.array([])
    charge = np.array([])

    for i, v in enumerate(voltages):
        logic = np.where(v > 0.025)
        c = currents[i]
        try:
            pv, uv = np.split(v[logic], 2)
            pc, uc = np.split(c[logic], 2)
        except ValueError:
            break

        try:
            logic = np.where(v < -0.025)
            nv, dv = np.split(v[logic], 2)
            nc, dc = np.split(c[logic], 2)
        except ValueError:
            break

        charge = np.append(charge, np.cumsum(np.append(pc, nc) - np.append(uc, dc)))
        v_charge = np.append(v_charge, np.append(pv, nv))

    ax = plt.subplot2grid((2, 2), (0, 0), colspan=2, rowspan=1)
    ax3 = plt.subplot2grid((2, 2), (1, 0), colspan=1, rowspan=1)
    ax4 = plt.subplot2grid((2, 2), (1, 1), colspan=1, rowspan=1)

    ax.plot(meas_time, voltage, linewidth=2, color="teal")

    for spine in ["left", "right", "top", "bottom"]:
        ax.spines[spine].set_linewidth(2)

    for label in ax.get_yticklabels() + ax.get_xticklabels():
        label.set_fontsize(20)
    ax.set_xlabel("Time, s", fontsize=20, labelpad=10)
    ax.set_ylabel("Voltage, V", fontsize=20, labelpad=10)
    ax2 = ax.twinx()
    ax2.locator_params(axis="y", nbins=7)
    ax2.plot(meas_time, current * 1e6, linewidth=2, color="tomato")
    for label in ax2.get_yticklabels():
        label.set_fontsize(20)
    ax2.set_ylabel("Current, $\mu$A", fontsize=20, labelpad=30, rotation=270)

    ax3.plot(voltage, current * 1e6, linewidth=2, color="tomato")
    for spine in ["left", "right", "top", "bottom"]:
        ax3.spines[spine].set_linewidth(2)

    for label in ax3.get_yticklabels() + ax3.get_xticklabels():
        label.set_fontsize(20)

    ax3.locator_params(axis="y", nbins=7)
    ax3.set_xlabel("Voltage, V", fontsize=20, labelpad=10)
    ax3.set_ylabel(r"Current, $\mu$A", fontsize=20, labelpad=10)

    ax4.plot(v_charge, charge * 1e6 * dt / area, linewidth=2, color="tomato")

    for spine in ["left", "right", "top", "bottom"]:
        ax4.spines[spine].set_linewidth(2)

    for label in ax4.get_yticklabels() + ax4.get_xticklabels():
        label.set_fontsize(20)

    ax4.set_xlabel("Voltage, V", fontsize=20, labelpad=10)
    ax4.set_ylabel("2P, uC/cm$^2$", fontsize=20, labelpad=5)

    plt.tight_layout()
    if save:
        try:
            plt.savefig(os.path.join(path, name), dpi=300)
        except FileNotFoundError:
            os.makedirs(path)
            plt.savefig(os.path.join(path, name), dpi=300)
    # plt.show()


def save_data(data, path, name):
    name = name + ".json"
    try:
        with open(os.path.join(path, name), "w") as f:
            json.dump(data, f, indent=4)
    except OSError:
        os.makedirs(path)
        with open(os.path.join(path, name), "w") as f:
            json.dump(data, f, indent=4)
