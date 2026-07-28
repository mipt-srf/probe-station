##########################
Why not raw SCPI commands?
##########################

Using :class:`~probe_station.measurements.b1500.B1500` class you can communicate with B1500 device through Python methods, without direct usage of SCPI commands and VISA API. 

Here is an example of the same script for quasistatic DC IV measurement using SMU written with raw SCPI commands and using :class:`~probe_station.measurements.b1500.B1500` class from this package:

.. TODO: check that both versions work

.. hint:: You can hover over the methods to see where they come from and click on them to go to the documentation page.

.. tab-set::

    .. tab-item:: B1500 class
       
        .. literalinclude:: ../../../examples/iv_sweep_b1500.py
           :language: python
           :linenos:

    .. tab-item:: Raw SCPI commands

        .. literalinclude:: ../../../examples/iv_sweep_raw_scpi.py
           :language: python
           :linenos:

Even though you probably won't understand every single line of the script at first, it is clear that using class methods makes the script much more readable and easier to understand and modify.

Also, you don't need to worry about parsing the data results, which can be quite painful when using binary format. 

.. tab-set::

    .. tab-item:: B1500 class
       
        .. literalinclude:: ../../../examples/iv_sweep_b1500.py
           :language: python
           :lines: 60-65
           :lineno-match:


    .. tab-item:: Raw SCPI commands

        .. literalinclude:: ../../../examples/iv_sweep_raw_scpi.py
           :language: python
           :lines: 44-50
           :lineno-match:

Note that ordinal number (1, 2, 3, etc.) is used to specify the required SMUs, contrary to raw SCPI where you need to specify slot number (see smth:section for details).

.. tab-set::

    .. tab-item:: B1500 class
       
        .. literalinclude:: ../../../examples/iv_sweep_b1500.py
           :language: python
           :lines: 22-23
           :lineno-match:


    .. tab-item:: Raw SCPI commands

        .. literalinclude:: ../../../examples/iv_sweep_raw_scpi.py
           :language: python
           :lines: 16-17
           :lineno-match: