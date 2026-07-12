#####
Usage
#####

There are 3 main ways to use this package:

1. You can use this package to :ref:`write your own scripts <Writing your scripts>` based on available B1500 Python interfaces (no need to write direct SCPI commands to send them using VISA)

2. You can run simple measurements (IV, CV sweeps, cycling, FET measurements (:math:`I_{ds}(V_{g}), I_{ds}(V_{ds})`)) using convenient GUI

3. You can analyze results of the measurements with built-in tools for processing specific measurements (e.g. extracting coercive fields from IV sweeps, batch processing of multiple measurements from complex experiments, etc.)

There are also more advanced features that will discussed further. (Writing GUI for your scripts, creating complex experiments)

.. _Writing your scripts:

Writing your scripts
====================

You can use :class:`B1500 <probe_station.measurements.b1500.B1500>` class to communicate with B1500 device through Python methods, without direct usage of SCPI commands and VISA API:

.. code-block:: python

    from probe_station import B1500
    inst = B1500()
    inst.smu4.enable()

Example of the same script for quasistatic DC IV measurement using SMU written with raw SCPI commands and using :class:`B1500 <probe_station.measurements.b1500.B1500>` class from this package:

.. note:: You can hover over the methods to see where they come from and click on them to go to the documentation page.

.. tab-set::

    .. tab-item:: B1500 class
       
        .. literalinclude:: ../../examples/iv_sweep_b1500.py
           :language: python
           :linenos:

    .. tab-item:: Raw SCPI commands

        .. literalinclude:: ../../examples/iv_sweep_raw_scpi.py
           :language: python
           :linenos:

Even though you probably won't understand every single line of the script at first, it is clear that using class methods makes the script much more readable and easier to understand and modify.

Also, you don't need to worry about parsing the data results, which can be quite painful when using binary format. 

.. tab-set::

    .. tab-item:: B1500 class
       
        .. literalinclude:: ../../examples/iv_sweep_b1500.py
           :language: python
           :lines: 61-66
           :lineno-match:


    .. tab-item:: Raw SCPI commands

        .. literalinclude:: ../../examples/iv_sweep_raw_scpi.py
           :language: python
           :lines: 44-50
           :lineno-match:

Note that ordinal number (1, 2, 3, etc.) is used to specify the required SMUs, contrary to raw SCPI where you need to specify slot number (see smth:section for details).

.. tab-set::

    .. tab-item:: B1500 class
       
        .. literalinclude:: ../../examples/iv_sweep_b1500.py
           :language: python
           :lines: 22-23
           :lineno-match:


    .. tab-item:: Raw SCPI commands

        .. literalinclude:: ../../examples/iv_sweep_raw_scpi.py
           :language: python
           :lines: 16-17
           :lineno-match:

.. seealso::
    
    onboarding?:smth pymeasure
        if you want to understand what methods are available.

    structure?:smth
        if you want to understand how the B1500 class is structured

    examples smth
        if you want to see more examples of using B1500 class for measurements

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

