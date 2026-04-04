"""Package for controlling the Keysight B1500 probe station and processing its data.

Provides:

* :class:`Dataset` — parse legacy ``.data`` files and select the appropriate handler.
* :func:`connect_instrument` — connect to the Agilent/Keysight B1500 over USB.
* ``analysis`` sub-package — batch processing, CV/IV handlers, helper functions.
* ``measurements`` sub-package — PyMeasure procedures for IV, CV, PUND, and cycling.
* ``experiments`` sub-package — high-level experiment orchestration scripts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dataset import Dataset
    from .measurements.b1500 import B1500
    from .measurements.common import connect_instrument
    from .measurements.keithley import Keithley2450Extended

__all__ = ["Dataset", "connect_instrument", "B1500", "Keithley2450Extended"]


def __getattr__(name: str):
    if name == "Dataset":
        from .dataset import Dataset

        return Dataset
    if name == "B1500":
        from .measurements.b1500 import B1500

        return B1500
    if name == "connect_instrument":
        from .measurements.common import connect_instrument

        return connect_instrument
    if name == "Keithley2450Extended":
        from .measurements.keithley import Keithley2450Extended

        return Keithley2450Extended
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
