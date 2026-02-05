import itertools
from pathlib import Path

from matplotlib import pyplot as plt
from numpy import sqrt

from probe_station.analysis.dataset import Dataset
from probe_station.measurements.voltage_sweeps.IV.WGFMU.procedure import (
    calculate_polarization,
)


class CyclingExperiment:
    def __init__(self, folder, area, thickness):
        self.folder = folder
        self.area = area
        self.thickness = thickness
        if not Path(folder).exists():
            raise ValueError(f"Folder {folder} does not exist.")
        # assert len(self.cycles) == len(self.smu_datasets) == len(self.cv_datasets) == len(self.wgfmu_datasets)

    @property
    def csvs(self):
        csvs = list(Path(self.folder).glob("*.csv"))
        csvs = sorted(csvs, key=lambda x: int(x.name.split("_")[0]))  # sort by number

        if "PgCycling" in csvs[-1].name:  # drop last if exp was interrupted and no data is measured
            csvs = csvs[:-1]
        return csvs

    @property
    def cv_datasets(self):
        return [Dataset(filename) for filename in self.csvs if "CvSweep" in filename.name]

    @property
    def smu_datasets(self):
        return [Dataset(filename) for filename in self.csvs if "_IvSweep" in filename.name]

    @property
    def wgfmu_datasets(self, top_voltage=5.0, mode="PUND"):
        return [Dataset(filename) for filename in self.csvs if "WgfmuIvSweep" in filename.name]

    @property
    def cycles(self):
        exp_cycles = [
            int(filename.name.split("_")[2].strip("cycles.csv"))
            for filename in self.csvs
            if "PgCycling" in filename.name
        ]
        cycles = list(itertools.accumulate(exp_cycles, initial=0))
        return cycles

    def cvs(self, drop_below=None):
        return CvBatchProcessing(self, drop_below=drop_below)

    def smu_ivs(self, drop_below=None, drop_above=None):
        return SmuBatchProcessing(self, drop_below=drop_below, drop_above=drop_above)

    def wgfmu_ivs(self, drop_below=None, drop_above=None):
        return WgfmuBatchProcessing(self, drop_below=drop_below, drop_above=drop_above)


class CvBatchProcessing:
    def __init__(self, experiment, drop_below=None):
        self.exp = experiment
        self.drop_below = drop_below
        self.cycles = self.exp.cycles.copy()
        self.datasets = self.exp.cv_datasets.copy()

        if self.drop_below is not None:
            self.drop_outlier_curves()

    def drop_outlier_curves(self):
        cycles_to_keep = []
        datasets_to_keep = []
        dropped_cycles = []

        for cycle, ds in zip(self.cycles, self.datasets):
            ds.handler.set_geometry(area=self.exp.area, thickness=self.exp.thickness)

            should_keep = True

            if ds.data.shape[0] == 0:
                # print("dropped")
                should_keep = False
            elif sum(ds.get_epsilon() < 1) > 0:
                # print(f"Cycle {cycle}: < 1")
                should_keep = False
            elif sum(ds.get_epsilon() < self.drop_below) > 0:
                # print(cycle)
                should_keep = False

            if should_keep:
                cycles_to_keep.append(cycle)
                datasets_to_keep.append(ds)
            else:
                dropped_cycles.append(cycle)

        self.cycles = cycles_to_keep
        self.datasets = datasets_to_keep
        print(f"Dropped cycles: {dropped_cycles}")

    def plot_eps_v(self, drop_below=None):
        for cycle, ds in zip(self.cycles, self.datasets):
            try:
                ds.handler.set_geometry(area=self.exp.area, thickness=self.exp.thickness)
                # ds.plot_epsilon(color="blue", alpha=0.2, label=cycle)
                ds.plot_epsilon(label=cycle)
            except Exception as e:
                print(f"Error in plot_eps_v: {e}, {ds}")

    def plot_eps_cycles(self, voltage, color=None):
        if self.datasets == []:
            print("No datasets to plot.")
            return
        epsilons = []
        for cycle, ds in zip(self.cycles, self.datasets):
            ds.handler.set_geometry(area=self.exp.area, thickness=self.exp.thickness)
            epsilon = ds.handler.get_epsilons_at_voltage(voltage)[1]
            epsilons.append(epsilon)
        print(self.exp.folder, self.exp.folder[-5:])
        plt.plot(self.cycles, epsilons, "o", label=self.exp.folder, color=color)

    def plot_coercive_cycles(self, drop_below=None):
        coercive_voltages = []
        for cycle, ds in zip(self.cycles, self.datasets):
            ds.handler.set_geometry(area=self.exp.area, thickness=self.exp.thickness)
            coercive_voltage = ds.handler.get_coercive_voltage()
            coercive_voltages.append(coercive_voltage)
        plt.plot(self.cycles, coercive_voltages, "o")


class SmuBatchProcessing:
    def __init__(self, experiment, drop_below=None, drop_above=None):
        self.exp = experiment
        self.drop_below = drop_below
        self.drop_above = drop_above
        self.cycles = self.exp.cycles.copy()
        self.datasets = self.exp.smu_datasets.copy()

        if self.drop_below is not None:
            self.drop_outlier_curves()

        if self.drop_above is not None:
            self.drop_above_outlier_curves()

    def drop_outlier_curves(self):
        cycles_to_keep = []
        datasets_to_keep = []
        dropped_cycles = []

        for cycle, ds in zip(self.cycles, self.datasets):
            should_keep = True

            if ds.data.shape[0] == 0:
                # print("dropped")
                should_keep = False
            elif sum(ds.data["Top electrode current"] < self.drop_below) > 0:
                # print(cycle)
                should_keep = False

            if should_keep:
                cycles_to_keep.append(cycle)
                datasets_to_keep.append(ds)
            else:
                dropped_cycles.append(cycle)

        self.cycles = cycles_to_keep
        self.datasets = datasets_to_keep
        print(f"Dropped cycles: {dropped_cycles}")

    def drop_above_outlier_curves(self):
        cycles_to_keep = []
        datasets_to_keep = []
        dropped_cycles = []

        for cycle, ds in zip(self.cycles, self.datasets):
            should_keep = True

            if sum(ds.data["Top electrode current"] > self.drop_above) > 0:
                # print(cycle)
                should_keep = False

            if should_keep:
                cycles_to_keep.append(cycle)
                datasets_to_keep.append(ds)
            else:
                dropped_cycles.append(cycle)

        self.cycles = cycles_to_keep
        self.datasets = datasets_to_keep
        print(f"Dropped cycles: {dropped_cycles}")

    def plot_current_v(self, indexes=None, drop_below=None):
        if not indexes:
            try:
                for cycle, ds in zip(self.cycles, self.datasets):
                    ds.plot(color="blue", alpha=0.2)
            except Exception as e:
                print(f"Error in plot_current_v: {e}, {ds}")
            finally:
                return

        for index in indexes:
            ds = self.datasets[index]
            label = f"{self.cycles[index]:.1e}"
            label = label.replace("e+0", r" \cdot 10^{").replace("e+", r" \cdot 10^{")
            label = label.replace("e-0", r" \cdot 10^{-").replace("e-", r" \cdot 10^{-")
            label = "$" + label + "}$"
            ds.plot(label=label)

    def plot_current_cycles(self, voltage, marker="o", color=None, alpha=1):
        currents = []
        for cycle, ds in zip(self.cycles, self.datasets):
            current = ds.handler.get_current_at_voltage(voltage)[1]
            currents.append(current)
        plt.plot(self.cycles, currents, marker, color=color, label=self.exp.folder, alpha=alpha)


class WgfmuBatchProcessing:
    def __init__(self, experiment, drop_below=None, drop_above=None):
        self.exp = experiment
        self.drop_below = drop_below
        self.drop_above = drop_above
        self.cycles = self.exp.cycles.copy()
        self.datasets = self.exp.wgfmu_datasets.copy()
        # print("Before dropping empty datasets:", len(self.cycles), len(self.datasets))
        # self.drop_empty_datasets()
        # print("After dropping empty datasets:", len(self.cycles), len(self.datasets))

        if self.drop_below is not None:
            self.drop_outlier_curves()

        if self.drop_above is not None:
            self.drop_above_outlier_curves()

    def drop_empty_datasets(self):
        cycles_to_keep = []
        datasets_to_keep = []
        dropped_cycles = []

        for cycle, ds in zip(self.cycles, self.datasets):
            should_keep = True

            if ds.data.shape[0] == 0:
                # print("dropped")
                should_keep = False

            if should_keep:
                cycles_to_keep.append(cycle)
                datasets_to_keep.append(ds)
            else:
                dropped_cycles.append(cycle)

        self.cycles = cycles_to_keep
        self.datasets = datasets_to_keep
        print(f"Dropped cycles: {dropped_cycles}")

    def drop_outlier_curves(self):
        cycles_to_keep = []
        datasets_to_keep = []
        dropped_cycles = []

        for cycle, ds in zip(self.cycles, self.datasets):
            should_keep = True

            if ds.data.shape[0] == 0:
                # print("dropped")
                should_keep = False
            elif sum(ds.data["Top electrode Current"] < self.drop_below) > 0:
                # print(cycle)
                should_keep = False

            if should_keep:
                cycles_to_keep.append(cycle)
                datasets_to_keep.append(ds)
            else:
                dropped_cycles.append(cycle)

        self.cycles = cycles_to_keep
        self.datasets = datasets_to_keep
        print(f"Dropped cycles: {dropped_cycles}")

    def drop_above_outlier_curves(self):
        cycles_to_keep = []
        datasets_to_keep = []
        dropped_cycles = []

        for cycle, ds in zip(self.cycles, self.datasets):
            should_keep = True

            if sum(ds.data["Top electrode Current"] > self.drop_above) > 0:
                # print(cycle)
                should_keep = False

            if should_keep:
                cycles_to_keep.append(cycle)
                datasets_to_keep.append(ds)
            else:
                dropped_cycles.append(cycle)

        self.cycles = cycles_to_keep
        self.datasets = datasets_to_keep
        print(f"Dropped cycles: {dropped_cycles}")

    def plot_iv(self, indexes=None):
        if indexes is None:
            for ds in self.datasets:
                if ds.procedure.mode == "PUND":
                    ds.plot()
        else:
            for index in indexes:
                ds = self.datasets[index]
                # if ds.procedure.mode == "PUND":
                label = f"{self.cycles[index]:.1e}"
                label = label.replace("e+0", r" \cdot 10^{").replace("e+", r" \cdot 10^{")
                label = label.replace("e-0", r" \cdot 10^{-").replace("e-", r" \cdot 10^{-")
                label = "$" + label + "}$"
                ds.plot(label=label)
            plt.legend(title="Cycles")

    def plot_polarization_cycles(self, color=None):
        polarizations = []
        print(len(self.cycles), len(self.datasets))
        for cycle, ds in zip(self.cycles, self.datasets):
            if (filtered_polarization := ds.data.get("Filtered Polarization current")) is None:
                print(11)
                filtered_polarization = ds.data["Polarization current"]
            polarization = calculate_polarization(
                ds.data["Time"], filtered_polarization, pad_size_um=sqrt(self.exp.area / 1e-12)
            )
            polarizations.append(polarization)
        plt.plot(self.cycles, polarizations, "o", color=color, label=self.exp.folder)
        plt.ylim(0)
        plt.xscale("log")
        plt.xlabel("Cycles")
        plt.ylabel(r"Polarization 2$P_r$ ($\mu C/cm^2$)")
        return polarizations

    def filter(self, mode="PUND", top_voltage=5.0):
        new_datasets = []
        for dataset in self.datasets:
            params = dataset.parameters
            if params["mode"].value == mode and params["voltage_top_first"].value == top_voltage:
                new_datasets.append(dataset)
        self.datasets = new_datasets
        if len(self.cycles) == len(self.datasets) + 1:
            self.cycles = self.cycles[1:]
        self.drop_empty_datasets()
        return self
