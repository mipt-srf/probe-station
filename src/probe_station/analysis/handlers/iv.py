"""Handler for current-voltage (IV) sweep result analysis."""

from probe_station.analysis.handlers.base import BaseHandler


class Iv(BaseHandler):
    """Handler for current-voltage sweep analysis and plotting."""

    def plot(self, color: str | None = None, label: float | str | None = None, alpha: float | None = None) -> None:
        """Plot the IV data.

        :param color: Line colour.
        :param label: Line label for the legend.
        :param alpha: Line transparency.
        """
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
