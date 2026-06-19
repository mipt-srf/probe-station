"""Handler for a FET output-characteristic sweep: Ids(Vds) at a fixed gate voltage."""

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from probe_station.analysis.handlers.base import BaseHandler

VDS_COLUMN = "Voltage"
IDS_COLUMN = "Source Current"


class FetIdsVds(BaseHandler):
    """Handler for a single Ids(Vds) output-characteristic sweep.

    Wraps the result of one :class:`SmuFetIdsVdsProcedure` run, i.e. a drain
    current sweep versus drain-source voltage recorded at a fixed gate voltage.
    """

    @property
    def gate_voltage(self) -> float:
        """Gate voltage at which the sweep was taken, in volts."""
        return self.parent.procedure.gate_voltage

    @property
    def vds(self) -> pd.Series:
        """Drain-source voltage sweep, in volts."""
        return self.data[VDS_COLUMN]

    @property
    def ids(self) -> pd.Series:
        """Drain (source-electrode) current, in amperes."""
        return self.data[IDS_COLUMN]

    def plot(
        self,
        color: str | None = None,
        label: float | str | None = None,
        alpha: float | None = None,
        *,
        logy: bool = False,
    ) -> None:
        """Plot the Ids(Vds) sweep.

        :param color: Line colour.
        :param label: Legend label.
        :param alpha: Line transparency.
        :param logy: Plot ``|Ids|`` on a logarithmic axis when ``True``.
        """
        self.plot_base(
            self.vds,
            self.ids.abs() if logy else self.ids,
            xlabel="Drain-source voltage, V",
            ylabel="Drain current, A",
            color=color,
            label=label,
            alpha=alpha,
        )
        if logy:
            plt.yscale("log")

    def get_current_at_vds(self, vds: float) -> float:
        """Return the drain current at *vds*, averaging the forward/reverse branches.

        :param vds: Drain-source voltage at which to read the current.
        :return: Interpolated drain current, or ``nan`` if *vds* is out of range.
        """
        branch_mean = self.ids.groupby(self.vds.round(4)).mean()
        return float(
            np.interp(
                vds,
                branch_mean.index.to_numpy(),
                branch_mean.to_numpy(),
                left=np.nan,
                right=np.nan,
            )
        )
