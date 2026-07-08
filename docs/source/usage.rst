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
--------------------

You can use B1500 class to communicate with B1500 device through Python methods, without direct usage of SCPI commands and VISA API:

.. code-block:: python

    from probe_station import B1500
    inst = B1500()
    inst.smu4.enable()

Example of the same script for quasistatic DC IV measurement using SMU written with raw SCPI commands and using B1500 class from this package:

.. tab-set::

    .. tab-item:: B1500 class
       
        .. literalinclude:: ../../examples/iv_sweep_b1500.py
           :language: python

    .. tab-item:: Raw SCPI commands

        .. literalinclude:: ../../examples/iv_sweep_raw_scpi.py
           :language: python

Even though you probably won't understand every single line of the script at first, it is clear that using class methods makes the script much more readable and easier to understand and modify. Also, you don't need to worry about parsing the data results, which can be quite painful when using binary format.

.. seealso::
    
    onboarding?:smth pymeasure
        if you want to understand what methods are available.

    structure?:smth
        if you want to understand how the B1500 class is structured

    examples smth
        if you want to see more examples of using B1500 class for measurements

    examples smth how to use smu and wgfmu

