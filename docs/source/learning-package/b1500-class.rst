###########
B1500 class
###########

:class:`~probe_station.measurements.b1500.B1500` class is a main class that you should use for writing your own measurement scripts.

Basically, this class is a thin wrapper around :class:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500` class from Pymeasure package. It is designed to add additional WGFMU functionality implemented in `keysight_b1530a <https://github.com/ilev-sergey/keysight-b1530a>`__ package. You can find more information about :class:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500` class in its documentation and on this page.

.. admonition:: Comment

    The reason why the wrapper class exists is that Pymeasure package `doesn't support <https://github.com/pymeasure/pymeasure/issues/1058>`__ devices based on DLLs. More details about WGFMU specifics can be found :doc:`here <wgfmu>`.

Initialization
==============

* :class:`~probe_station.measurements.b1500.B1500` class can be imported using

  .. code-block:: python

      from probe_station.measurements.b1500 import B1500

  or simply

  .. code-block:: python

      from probe_station import B1500

* Object of this class can be created using

  .. code-block:: python

      b = B1500()

  On initialization, it will try to :ref:`connect <explanation/connection:i/o layer>` to the instrument using USB address (same for both stations). On success, it will query and initialize all available units dynamically.

* :ref:`Data format <data_formatting>` for retrieving data is set using

  .. code-block:: python

      b.data_format(output_format=1, mode=1)

.. link to __init__

Main functionality
==================

Once initialized, the object of :class:`~probe_station.measurements.b1500.B1500` class can be used to configure the instrument, units, run measurements and retrieve data. The main functionality is described in the following sections.

.. _accessing-units:

Accessing units
---------------

Each unit can be accessed using either corresponding collection or using an attribute.

* For example, to access SMU1 you can use either

  .. code-block:: python

      b.smus[1]

  or

  .. code-block:: python

      b.smu1

* CMU is accessible using

  .. code-block:: python

      b.cmu

  since only one CMU can be present in the instrument.

* SPGU channels can be accessed using

  .. code-block:: python

      b.spgu1.ch1
      b.spgu1.ch2

* WGFMU channels can be accessed using

  .. code-block:: python

      b.wgfmu1 # channel 1 of WGFMU1
      b.wgfmu2 # channel 2 of WGFMU1

  The inconsistency in SPGU and WGFMU channels access is due to historical reasons.

.. TODO: fix for consistency with SPGU

.. admonition:: Autocompletion
    :collapsible: closed

    Both forms are autocompleted in IDEs.

    Collections are typed, so ``.smus[1]`` will be correctly autocompleted by default even if collection is empty.

    Because exact initialized units are known only in runtime, they are not hinted in IDEs. So, the units that both probe stations have in common (``smu1`` to ``smu4``, ``spgu1``, ``wgfmu1``, ``wgfmu2``, ``rsu1``, ``rsu2``) are additionally declared as static attributes on :class:`~probe_station.measurements.b1500.B1500` to provide autocompletion support.

Collections are also the form to use when the channel number is a variable rather than a literal, which is usually the case in measurement code:

.. code-block:: python

    smu = b.smus[gate_channel]

Measurement functionality
-------------------------

To see supported functionality of each unit, check documentation of corresponding class: :class:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500`, :class:`~pymeasure.instruments.agilent.agilentB1500.SMU`, :class:`~pymeasure.instruments.agilent.agilentB1500.CMU`, :class:`~pymeasure.instruments.agilent.agilentB1500.SPGU`, :class:`~keysight_b1530a.wgfmu.WGFMU`, :class:`~probe_station.measurements.rsu.RSU`.

.. TODO: add short summary with most used methods for each unit

AgilentB1500 class
==================

This class wraps raw :ref:`FLEX <explanation/b1500-specifics:flex commands>` commands into Python methods and implemented as part of `Pymeasure <https://github.com/pymeasure/pymeasure>`__ package. For most of the instruments (generators, oscilloscopes, etc.), the methods and the class itself are quite simple. However, this is not always the case for B1500 due to its :doc:`specifics <../explanation/b1500-specifics>` and complexity. Here, I will shortly explain how this driver is structured and what's the logic behind some of not obvious functionality.

.. _data_formatting:

Data formatting
---------------

The device supports 13 data formats that differ in resolution, termination and so on (see page 4-119 of :ref:`programming guide <reference/manuals:manuals>` for details). The main difference is whether the data format is binary or ASCII. At the moment, only ASCII formats are supported in Pymeasure. This results in an incompatibility of this package with Matlab codebase, which uses binary format. Specifically, you need to use "Clear Instrument" in Matlab that will reset the instrument and set the data format to binary before running Matlab scripts from its GUI.

Ideally, binary format support should be added to Pymeasure to have a seamless integration with Matlab codebase, but I didn't have time to finish `this work <https://github.com/ilev-sergey/pymeasure/commit/2dfdc86055a247e4ef4f451c551806fbec8d67cb>`__

Anyway, to retrieve the data after a measurement, you can use following methods:

* :meth:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500.read_data` - returns data as a :class:`pandas.DataFrame`. Number of points should be specified.
* :meth:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500.read_channels` - returns data for a single measurement point for a given number of channels (e.g. pass 1 if only channel is specified in :meth:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500.meas_mode` method).

They will parse and process data for you. Alternatively, you can do it yourself. Here is the snippet that shows what is actually returned by the instrument and how it is processed in the case of ASCII format. It may be useful if you want to implement binary format support in Pymeasure or add some additional measurement functionality.

from probe_station import B1500
b = B1500()
b.data_format(output_format=1, mode=1)

raw_data = b.write(f"TTIV {b.smu1.id}")
raw_data = b.read()
raw_data

split_data = raw_data.split(',')
time_data, voltage_data, current_data = split_data
split_data

return tuple(data_format.format_single(element)[3] for element in split_data)

b._data_format.format_single(raw_data)

The same processing is done automatically using implemented methods
time, current, voltage = b.smu1.measure_iv(timestamp=True, current_range=0, voltage_range=0)
time, current, voltage

Here, the data is returned momentarily since it is a high-speed spot measurement. For a sweep measurement, the measurement is run first with :meth:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500.send_trigger` method and then the data is retrieved with :meth:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500.read_data` or :meth:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500.read_channels` method. The internal processing logic stays mostly the same as shown above.

See an example below

ADC mode
========

HR, HS, etc.


Querying
========


Enums
=====
