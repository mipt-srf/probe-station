"""Package for controlling the Keysight B1500 probe station and processing its data.

Provides:

* :class:`Dataset` — parse legacy ``.data`` files and select the appropriate handler.
* :func:`connect_instrument` — connect to the Agilent/Keysight B1500 over USB.
* ``analysis`` sub-package — batch processing, CV/IV handlers, helper functions.
* ``measurements`` sub-package — PyMeasure procedures for IV, CV, PUND, and cycling.
* ``experiments`` sub-package — high-level experiment orchestration scripts.
"""

from .dataset import Dataset
from .measurements.common import connect_instrument

__all__ = ["Dataset", "connect_instrument"]
