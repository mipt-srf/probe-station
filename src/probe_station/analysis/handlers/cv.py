from probe_station.analysis.handlers.base import BaseHandler


class Cv(BaseHandler):
    def plot(self) -> None:
        self.plot_base(
            self.data["Voltage"],
            self.data["Capacitance"],
            xlabel="Voltage",
            ylabel="Capacitance",
            label="Capacitance",
        )

    def plot_resistance(self) -> None:
        self.plot_base(
            self.data["Voltage"],
            self.data["Resistance"],
            xlabel="Voltage",
            ylabel="Resistance",
            label="Resistance",
            color="tab:red",
        )

    def plot_epsilon(
        self,
        area: float,
        thickness: float,
        color: str | None = None,
        label: float | str | None = None,
        alpha: float | None = None,
    ) -> None:
        epsilon0 = 8.854e-12
        epsilon = self.data["Capacitance"] / epsilon0 / area * thickness
        self.plot_base(
            x_data=self.data["Voltage"],
            y_data=epsilon,
            xlabel="Voltage, V",
            ylabel="Dielectric constant",
            label=label,
            color=color,
            alpha=alpha,
        )
