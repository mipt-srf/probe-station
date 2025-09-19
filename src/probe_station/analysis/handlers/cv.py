from matplotlib import pyplot as plt

from probe_station.analysis.handlers.base import BaseHandler


class Cv(BaseHandler):
    def plot(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlabel("Voltage")
        ax.set_ylabel("Capacitance")
        ax.plot(self.data["Voltage"], self.data["Capacitance"], label="Capacitance")
        plt.show()

    def plot_resistance(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlabel("Voltage")
        ax.set_ylabel("Resistance")
        ax.plot(self.data["Voltage"], self.data["Resistance"], color="tab:red", label="Resistance")
        plt.show()

    def plot_epsilon(
        self,
        area: float,
        thickness: float,
        color: str | None = None,
        label: float | str | None = None,
    ) -> None:
        epsilon0 = 8.854e-12
        epsilon = self.data["Capacitance"] / epsilon0 / area * thickness
        plt.plot(self.data["Voltage"], epsilon, label=label, color=color)
        plt.ylabel("Dielectric constant")
        plt.xlabel("Voltage, V")
