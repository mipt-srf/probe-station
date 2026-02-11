.. _index:

|name|
======

|name| is a Python package for controlling and processing data from the
Keysight/Agilent B1500 probe station. It provides:

* **Measurement procedures** — ready-made PyMeasure procedures for IV sweeps
  (SMU & WGFMU), CV sweeps, PUND cycling, FET characterisation, and more.
* **Data parsing** — readers for legacy ``.data`` files (PQ-PUND, DC IV, CV,
  PUND double) and new PyMeasure ``.csv`` results.
* **Analysis helpers** — batch processing of cycling experiments, polarisation
  calculation, leakage-current fitting, and plotting utilities.

Documentation is current as of |today|.

Check out the :doc:`getting_started` section for further information.

.. toctree::
    :glob:
    :titlesonly:
    :caption: Contents:

    getting_started
    contribution
    installation_editable
    api

.. note::

   This project is under active development.
