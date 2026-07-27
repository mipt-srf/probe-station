
Advanced usage
==============

Writing GUI for your scripts
----------------------------

When you have a working :ref:`script <Writing your scripts>` that does what your need you can easily wrap GUI around that. The main idea here is that all the logic corresponding to the measurement itself (configuring measurement parameters, starting the measurement, retrieving the data) lives in the script itself. In the GUI part you call corresponding methods from script and add parameters required for your measurement as GUI fields. Detailed description is available in structure:smth.

.. TODO: update scripts so that logic separation really exists (startup actions are still present in procedures)

.. TODO: допиши - наверное проще всего разобрать на реальном примере, что делает каждая строчка, отнаследовавшись от BaseProcedure

Creating complex experiments
----------------------------

Since most of the measurements in the package are modular you can easily construct a complex experiment using measurements as building blocks.

Running measurements in Python (single procedure)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It's not possible to manually call methods of procedures that you implement when :ref:`building GUI <usage:Writing GUI for your scripts>`. Instead, you should either call methods of raw script or use :func:`~probe_station.experiments.common.run` that might induce a small delay between measurements

.. caution:: Despite that this functionality is powerful, you should always think whether it's really worth to use that for your specific case. Sometimes, building some specific thing using framework can be more awkward than implementing it from scratch. If you think this is your case, consider to drop down a level and implement it as a measurement or even as a simple script based on :class:`~probe_station.measurements.b1500.B1500` class.

