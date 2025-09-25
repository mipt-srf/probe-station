from probe_station.analysis.handlers.base import BaseHandler


class Iv(BaseHandler):
    def plot(self, color: str | None = None, label: float | str | None = None, alpha: float | None = None) -> None:
        self.plot_base(
            self.data["Top electrode voltage"],
            self.data["Filtered Polarization current"],
            # self.data["Top electrode Current"],
            xlabel="Voltage",
            ylabel="Polarization current",
            color=color,
            label=label,
            alpha=alpha,
        )
