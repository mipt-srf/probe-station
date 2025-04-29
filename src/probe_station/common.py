from matplotlib import pyplot as plt


def get_coercive_voltages(voltages, currents) -> tuple[float, float]:
    """Get positive and negative coercive voltage from the given voltages and currents.

    :param voltages: Series of voltages.
    :param currents: Series of currents.

    :return: Tuple of negative and positive coercive voltages.
    """
    negative_peak_idx = currents.idxmin()
    positive_peak_idx = currents.idxmax()

    negative_coercive_field = voltages.loc[negative_peak_idx]
    positive_coercive_field = voltages.loc[positive_peak_idx]

    return negative_coercive_field, positive_coercive_field


def plot_vlines(values: list[float], color: str = "r", label: str = "") -> None:
    """Plot vertical lines at specified values.

    :param values: List of values where vertical lines will be plotted.
    :param color: Color of the vertical lines.
    :param label: Label for the vertical lines in the legend.
    """
    for value in values:
        plt.axvline(x=value, color=color, linestyle="dashed", label=label)
    if label:
        plt.legend()
