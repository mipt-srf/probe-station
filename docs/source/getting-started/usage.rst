#####
Usage
#####

There are 3 main ways to use this package:

1. You can use this package to :ref:`write your own scripts <Writing your scripts>` based on available B1500 Python interfaces (no need to write direct SCPI commands to send them using VISA)

2. You can run simple measurements (IV, CV sweeps, cycling, FET measurements (:math:`I_{ds}(V_{g}), I_{ds}(V_{ds})`)) using convenient GUI

3. You can analyze results of the measurements with built-in tools for processing specific measurements (e.g. extracting coercive fields from IV sweeps, batch processing of multiple measurements from complex experiments, etc.)

There are also more advanced features that will `discussed further <usage:Advanced usage>`.

Below is a brief overview of each of the usage options. For more details, see corresponding sections.

.. _Writing your scripts:

Write your scripts
==================

You can use :class:`~probe_station.measurements.b1500.B1500` class to communicate with B1500 device through Python methods, without direct usage of SCPI commands and VISA API:

.. code-block:: python

    from probe_station import B1500
    inst = B1500()
    inst.smu4.enable()

.. TODO: add tutorial, etc. badges

.. seealso::

    :doc:`../tutorial/writing-your-first-script`
        if you want to learn by example and understand what each line of the script does

    :doc:`../learning-package/why-not-raw-scpi`
        if you want to see why using B1500 class is more convenient than using raw SCPI commands

    `Script examples <https://github.com/search?q=repo%3Amipt-srf%2Fprobe-station%20runner.py&type=code>`__
        if you want to see more examples of using B1500 class for measurements

    :doc:`../learning-package/structure`
        if you want to understand how the B1500 class is structured

    :class:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500` class documentation
        if you want to understand what methods of B1500 class are available to use in your scripts.


    examples smth how to use smu and wgfmu

Running measurements with GUI
=============================

Most of avaiable measurements can be run using GUI. You can run the main :ref:`launcher <structure:Launcher>` in three ways:

.. note:: Presence of ``(.venv)`` indicates that command must be executed in the virtual environment with :doc:`installed <installation>` package

- Run ``probe-station`` command in terminal

  .. code-block:: console

      (.venv) probe-station

  Alternatively, use `uv <https://docs.astral.sh/uv/getting-started/installation/>`_.  for automatic installation on run

  .. code-block:: console

      uv run --extra measurements probe-station

- Run ``launcher.py`` script located in :file:`src/probe_station/measurements/` folder using explorer, IDE or terminal

  .. code-block:: console

      (.venv) python src/probe_station/measurements/launcher.py

- Run :func:`probe_station.measurements.launcher.main` inside Python code

  .. code-block:: python

      >>> from probe_station.measurements.launcher import main as run_launcher
      >>> run_launcher()

The launcher contains the buttons for running measurements GUIs as well as links to the repository on GitHub and this documentation.

.. TODO: Add buttons

.. TODO: Add gif cmd: uv run -> launcher -> measurement GUI -> measurement launch

Data processing
===============

Data access
-----------

You can use convenient properties to quickly retrieve the data from datafiles as :class:`pandas.DataFrame`.

.. jupyter-execute::

    from probe_station.analysis.dataset import Dataset
    ds = Dataset("data/example_cv.csv")
    ds.data

Also, parameters that were used for the measurements as well as metadata can be accessed.

.. jupyter-execute::

    ds.parameters

.. jupyter-execute::

    ds.parameters["ac_voltage"].value

.. jupyter-execute::

    ds.metadata
    
.. jupyter-execute::

    ds.metadata["start_time"].value

This functionality is available for all datafiles produced by :class:`~probe_station.measurements.pymeasure_base.BaseProcedure` or :class:`~pymeasure.experiment.procedure.Procedure` -based measurements.

Data plotting
-------------

Since ``.data`` is presented as :class:`pandas.DataFrame` you can always quickly plot it

.. jupyter-execute::

    ds.data.plot(x="Voltage", y="Capacitance");

However, it might not be convenient when you want to process lots of datafiles with different types of data as you need to specify data columns to plot. For this case, there are structure:handlers that are procedure-specific but have common ``.plot`` methods. So, you can do simply following.

.. jupyter-execute::

    ds.plot()

Extracting characteristics from raw data
----------------------------------------

Some of the common processing specific to each procedure is provided by structure:handler as well.

E.g. you can calculate dielectric constant versus field curve as follows

.. jupyter-execute::

    ds.plot_epsilon(area=(50e-6) ** 2, thickness=10e-9)

There are also other methods that might be useful for processing multiple files at once and extracting some patterns

.. jupyter-execute::

    ds.handler.get_coercive_voltage()

.. jupyter-execute::

    ds.handler.get_epsilons_at_voltage(1)

.. warning::

    Since the type of handler that should be used for specific datafile is determined in run time, the IDE autocompletion and type hints don't work very well. You might want to look at corresponding handler docs (:class:`~probe_station.analysis.handlers.cv.Cv`, :class:`~probe_station.analysis.handlers.iv.Iv`, :class:`~probe_station.analysis.handlers.fet_ids_vds.FetIdsVds`) yourself to see which methods are available.
    
    You can also see available methods and properties from code.

    .. jupyter-execute::

        [attr for attr in dir(ds.handler) if not (attr.startswith("__"))]

Matlab data processing (deprecated)
-----------------------------------

It's also possible to use this package for processing datafiles produced by Matlab codebase.

.. admonition:: Comment

    In fact, the initial idea of this package was to simplify routine processing of these files. However, it quickly became obvious that both measurements, processing and even the software itself can be implemented in a more structured way. So, I switched to platform-based approach.

Supported measurements from Matlab codebase are represented by :class:`~probe_station.analysis.matlab.pq_pund.PQ_PUND`, :class:`~probe_station.analysis.matlab.dc_iv.DC_IV`, :class:`~probe_station.analysis.matlab.cv.CV` and :class:`~probe_station.analysis.matlab.pund_double.PUND_double` classes. The idea behind is similar: you can use common :class:`~probe_station.analysis.matlab.dataset.Dataset` class that will choose appropriate handler for your datafile and parse it accordingly.

.. TODO: example (Dataset, basic .plot, specific things)
also how to see avaiable methods

Despite that utils for Matlab datafiles processing it's still a part of the package as well, I would recommend to switch to using package's measurements as they are implemented as part of the ecosystem and can be easier processed in the future.

