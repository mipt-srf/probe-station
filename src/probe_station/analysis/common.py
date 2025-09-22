import logging

import numpy as np
import pandas as pd


def get_y_at_x(
    x_data: np.ndarray | pd.Series, y_data: np.ndarray | pd.Series, target_x: float, tolerance: float = 5e-2
) -> float:
    """Return the y value at the specified x value by interpolation.

    :param x_data: Array containing the x values (numpy array or pandas Series).
    :param y_data: Array containing the y values (numpy array or pandas Series).
    :param target_x: The x value at which to get the y value.
    :param tolerance: Maximum allowed difference between target and actual x value.
    :return: The y value at the specified x value.
    """
    idx = np.abs(x_data - target_x).argmin()
    closest_x = x_data[idx]
    if abs(closest_x - target_x) > tolerance:
        logging.warning(
            "x value %s not found in data. Closest is %s",
            target_x,
            closest_x,
        )
    return np.abs(y_data[idx])


def find_x_at_min_y(x_data: np.ndarray | pd.Series, y_data: np.ndarray | pd.Series) -> float:
    """Return the x value at which the y value is minimum.

    :param x_data: Array containing the x values (numpy array or pandas Series).
    :param y_data: Array containing the y values (numpy array or pandas Series).
    :return: The x value at which the y value is minimum.
    """
    idx = np.abs(y_data).argmin()
    return x_data[idx]


def find_x_at_max_y(x_data: np.ndarray | pd.Series, y_data: np.ndarray | pd.Series) -> float:
    """Return the x value at which the y value is maximum.

    :param x_data: Array containing the x values (numpy array or pandas Series).
    :param y_data: Array containing the y values (numpy array or pandas Series).
    :return: The x value at which the y value is maximum.
    """
    idx = np.abs(y_data).argmax()
    return x_data[idx]
