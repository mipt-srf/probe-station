Usage
=====

Legacy data files
-----------------

The legacy `Dataset` class reads ``.data`` files produced by the probe station
software and dispatches processing to the appropriate handler (``PQ_PUND``,
``DC_IV``, ``CV``, or ``PUND_double``):

.. code-block:: python

    from probe_station import Dataset as DS
    import matplotlib.pyplot as plt

    ds = DS(r"path\to\data.data")

    # Quick plot via the handler
    ds.plot()

    # Access raw dataframes
    df = ds.dataframes[0]
    plt.plot(df["Bias"], df["Current"])

PyMeasure CSV results
---------------------

For data produced by the new measurement procedures (``IvSweepProcedure``,
``CvSweepProcedure``, ``WgfmuIvSweepProcedure``), use the analysis
`~probe_station.analysis.dataset.Dataset`:

.. code-block:: python

    from probe_station.analysis.dataset import Dataset

    ds = Dataset("results/1_IvSweepProcedure.csv")
    ds.plot()

Batch analysis of cycling experiments
--------------------------------------

Use `~probe_station.analysis.ultimate_processing.CyclingExperiment` to
process an entire cycling folder at once:

.. code-block:: python

    from probe_station.analysis.ultimate_processing import CyclingExperiment

    exp = CyclingExperiment(
        folder="results/",
        area=25e-12,       # pad area in m²
        thickness=100e-9,  # film thickness in m
    )

    # Plot dielectric constant vs voltage for every CV sweep
    exp.cvs().plot_eps_v()

    # Plot polarisation vs number of cycles
    exp.wgfmu_ivs().plot_polarization_cycles()

Plotting utilities
------------------

The `~probe_station.utilities` module offers helpers for plotting multiple
files, colour gradients, line labelling, and transistor characterisation:

.. code-block:: python

    from probe_station.utilities import plot_in_folder, characterize_transistor

    plot_in_folder(r"path\to\folder", labels=["1 V", "2 V", "3 V"])

Running measurements
--------------------

Measurement procedures can be launched from a PyMeasure GUI or
programmatically:

.. code-block:: python

    from probe_station import connect_instrument

    b1500 = connect_instrument()

See the ``measurements`` sub-package for available procedures.