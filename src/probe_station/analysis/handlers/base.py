import numpy as np
import pandas as pd
import scienceplots  # noqa: F401
from matplotlib import pyplot as plt


class BaseHandler:
    def __init__(self, parent):
        self.parent = parent

    @property
    def data(self):
        return self.parent.data

    @property
    def parameters(self):
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
        plt.style.use(["science", "no-latex", "notebook"])
        plt.plot(x_data, y_data, label=label, alpha=alpha, color=color)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        if label:
            plt.legend()
