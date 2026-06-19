"""Handler for current-voltage (IV) sweep result analysis."""

from probe_station.analysis.handlers.base import BaseHandler
from probe_station.measurements.wgfmu._waveforms import (
    calculate_polarization,
    pund_polarization_current,
)


class Iv(BaseHandler):
    """Handler for current-voltage sweep analysis and plotting."""

    def polarization_current(self):
        """Return ``(time, voltage, polarization_current)`` for the PUND sweep.

        The polarization current is the P-U / N-D subtracted switching current.
        It is taken from the bottom (sense) electrode whenever that channel was
        recorded: the driven top electrode also carries a large charging and
        leakage current that swamps the switching signal, so the stored
        top-based ``Polarization current`` columns are unreliable for
        two-terminal capacitors.  Data measured without a bottom electrode falls
        back to the stored (filtered) top-based column.
        """
        data = self.data
        bottom = data.get("Bottom Electrode Current")
        if bottom is not None and bottom.notna().any():
            clean = data[["Time", "Top Electrode Voltage", "Bottom Electrode Current"]].dropna()
            current = pund_polarization_current(
                clean["Top Electrode Voltage"].to_numpy(), clean["Bottom Electrode Current"].to_numpy()
            )
            return clean["Time"].to_numpy(), clean["Top Electrode Voltage"].to_numpy(), current

        current = data.get("Filtered Polarization Current")
        if current is None:
            current = data["Polarization Current"]
        return data["Time"].to_numpy(), data["Top Electrode Voltage"].to_numpy(), current.to_numpy()

    def polarization(self, pad_size_um):
        """Switched polarization 2Pr (uC/cm^2) for the sweep, or NaN if it failed.

        :param pad_size_um: Pad edge length in micrometres.
        """
        times, _, current = self.polarization_current()
        if len(times) < 4:
            return float("nan")
        return calculate_polarization(times, current, pad_size_um)

    def plot(self, color: str | None = None, label: float | str | None = None, alpha: float | None = None) -> None:
        """Plot the polarization current against the top electrode voltage.

        :param color: Line colour.
        :param label: Line label for the legend.
        :param alpha: Line transparency.
        """
        _, voltage, current = self.polarization_current()
        self.plot_base(
            voltage,
            current,
            xlabel="Voltage",
            ylabel="Polarization Current",
            color=color,
            label=label,
            alpha=alpha,
        )
