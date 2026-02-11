"""Base handler class for analysis of PyMeasure result datasets."""

import numpy as np
import pandas as pd
import scienceplots  # noqa: F401
from matplotlib import pyplot as plt


class BaseHandler:
    """Base class for analysis handlers that wrap a PyMeasure ``Results`` object."""

    def __init__(self, parent):
        """Initialize the handler with a parent ``Results`` object.

        :param parent: A PyMeasure ``Results`` instance whose data and parameters
            are accessed through this handler.
        """
        self.parent = parent

    @property
    def data(self):
        """Return the parent's data DataFrame."""
        return self.parent.data

    @property
    def parameters(self):
        """Return the parent's procedure parameters dictionary."""
        return self.parent.parameters

    def plot_base(
        self,
        x_data: np.ndarray | pd.Series,
        y_data: np.ndarray | pd.Series,
        xlabel: str,
        ylabel: str,
        label: str = None,
        alpha: float = 1.0,
        color: str = None,
    ) -> None:
        """Plot *y_data* vs *x_data* with science-style formatting.

        :param x_data: X-axis data.
        :param y_data: Y-axis data.
        :param xlabel: X-axis label.
        :param ylabel: Y-axis label.
        :param label: Legend label.
        :param alpha: Line transparency.
        :param color: Line colour.
        """
        plt.style.use(["science", "no-latex", "notebook"])
        plt.plot(x_data, y_data, label=label, alpha=alpha, color=color)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        if label:
            plt.legend()

    def split_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split the data into forward and reverse sweeps.

        :return: A tuple containing the forward and reverse DataFrames.
        """
        mid_idx = len(self.data) // 2
        forward = self.data.iloc[:mid_idx].reset_index(drop=True)
        reverse = self.data.iloc[mid_idx:].reset_index(drop=True)
        return forward, reverse
