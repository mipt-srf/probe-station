#################
Package Structure
#################

The package consists of 3 subpackages: :mod:`probe_station.measurements`, :mod:`probe_station.analysis` and :mod:`probe_station.experiments`. The first one is the main one and contains functionality for running measurements. The second one is for analyzing the data obtained from measurements. The :mod:`probe_station.experiments` subpackage is responsible for running complex experiments, which are a set of sequential measurements.

.. note:: The trees below are generated from the repository at build time, so they always match the current layout. Every entry links to its source on GitHub.

.. filetree:: src
   :max-depth: 2

:mod:`probe_station.measurements`
=================================

This part contains the main functionality of the package. It contains functionality for working with Agilent B1500. It is also responsible for running measurements using GUI and saving data to files.

.. filetree:: src/probe_station/measurements
   :max-depth: 1

B1500 class
-----------

B1500 class is the main class that is responsible for working with Agilent B1500. It contains methods for configuring the instrument, running measurements and retrieving data. You should use this class if you want to implement your own measurement script. It can be imported using

.. code-block:: python

    from probe_station.measurements.b1500 import B1500

or simply

.. code-block:: python

    from probe_station import B1500

Basically, this class is a thin wrapper around :class:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500` class from Pymeasure package. It is designed to add additional WGFMU functionality implemented in `keysight_b1530a <https://github.com/ilev-sergey/keysight-b1530a>`__ package. You can find more information about :class:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500` class in its documentation and on this :ref:`page <explanation/b1500:b1500>` WGFMU specifics :doc:`here <wgfmu>`.

Launcher
--------

Launcher is a GUI that collects most of basic available measurements and allows you to open GUI for each measurement. See more details in :ref:`running measurements with GUI <getting-started/usage:Running measurements with GUI>` section.

Measurement scripts
-------------------

Scripts are separated by hardware unit they use. E.g. you can find all available scripts that use SMU in :file:`src/probe_station/measurements/smu` folder.

.. filetree:: src/probe_station/measurements/smu
   :max-depth: 1

Each script has ``runner`` in its name and contains commands for running a specific measurement. You can use them as examples for writing your own scripts. See more details in :doc:`writing your first script <../tutorial/writing-your-first-script>` section.

If script uses multiple units simultaneously, the corresponding folder is named after the unit that is used as a main one.

.. Is it the right place? 

Measurement GUI
---------------

Most of the scripts has corresponding GUI that allows you to customize measurement parameters, run the measurement and visualize the results. The GUI is implemented using Pymeasure package and is located next to the corresponding script. E.g. GUI for :file:`src/probe_station/measurements/smu/iv_sweep_runner.py` script is located in :file:`src/probe_station/measurements/smu/iv_sweep.py` file.

GUI can be run using :ref:`launcher <getting-started/usage:Running measurements with GUI>` or by running the GUI script directly.

:mod:`probe_station.analysis`
=============================

This part allows you to analyze the data obtained from measurements. It supports datafiles produced by the measurement scripts from :mod:`probe_station.measurements` subpackage and from main Matlab scripts that can be launched using GUI. It contains functionality for parsing the data, plotting it and extracting some parameters from it. Some of the experiments are also supported.

.. filetree:: src/probe_station/analysis
   :max-depth: 1

:mod:`probe_station.experiments`
================================

By experiments I mean a set of sequential measurements that are run one after another. This part contains several pre-defined experiment scripts. You can use them or learn how to create your own in :ref:`creating complex experiments <learning-package/advanced-usage:creating complex experiments>` page.

.. filetree:: src/probe_station/experiments
   :max-depth: 1
