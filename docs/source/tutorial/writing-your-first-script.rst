#########################
Writing your first script
#########################

In this section we will walk through the process of writing a script for a simple measurement using the B1500.

Typically, there are 3 main steps that each measurement script does:

1. Configure the measurement parameters (sweep settings, integration time, current range, etc.)

2. Start the measurement and wait for it to finish

3. Retrieve the data from the instrument, parse it and save it to a datafile for future analysis

Let's see how this works in practice on a simple example of a DC IV sweep using SMU.

DC IV sweep using SMU
=====================

Direct current (DC) current-voltage (IV) sweep is one of the most basic measurements for device characterization. One of the contacts of the device is connected to the biased SMU and the other one is grounded. The SMU sweeps the voltage from a start value to an end value and measures the current flowing through the device at each voltage point.

Here is a full version if you want to see the whole script at once. We will go through it step by step below.

.. admonition:: DC IV sweep script
    :collapsible: closed

    .. literalinclude:: ../../../examples/iv_sweep_b1500.py
        :language: python

.. tip:: Remember to :doc:`install <../getting-started/installation>` the package first

* First, we need to import and initialize the :class:`~probe_station.measurements.b1500.B1500` class that provides an interface to the B1500 instrument:

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 3, 4, 14-16

  Under the hood, it will :doc:`connect <../explanation/connection>` to the instrument, :meth:`query <pymeasure.instruments.agilent.agilentB1500.AgilentB1500.query_modules>` available units and :ref:`initialize <accessing-units>` corresponding classes for each unit.

* Optionally, you can reset the instrument, so that it is in a known state before configuring:

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 17

  It is not a strict requirement, since you should always configure all the parameters you need for your measurement anyway, but it is a good practice to improve reproducibility. However, you often want to avoid resetting when doing multiple measurements in a row (see :ref:`creating experiments <learning-package/advanced-usage:creating complex experiments>`).

* Next, setup the :ref:`data format <explanation/b1500:Data formatting>` that is used when retrieving the data from the instrument.

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 18

  Unless you need a binary format, you can use the default ASCII format as above

* It's useful to have a separate block where you specify main parameters that you often change. Note, that ordinal numbers are used for SMU (see :ref:`SMU naming conventions <learning-package/how-it-works:SMU naming conventions>`).

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 20-25

* Next, we setup the :ref:`selectors <learning-package/how-it-works:Switching between units>`. Here, we enable SMU/SPGU selector and select SMU output for both selector output channels. Note, that :ref:`enums <explanation/b1500:Enums>` are used for better readability.

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 27-29

* After that, SMUs are enabled

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 31-35

* If you didn't reset the instrument, you may want to explicitly set zero voltage for SMUs

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 37-38

* Next, we enable timestamp, so that each measurement point will have a corresponding timestamp.

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 40

* Setup the measurement mode for used units. Here we specify that ``smu_top`` will be used for staircase sweep measurement.

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 41

* Setup measurements settings for measuring unit. Here we specify that ``smu_top`` will measure current and use automatic range selection (use ``0`` for autorange).

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 42-43

* Setup ADC settings. See :ref:`ADC mode <explanation/b1500:ADC mode>` for details.

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 44-45

* Configure settings for staircase sweep.

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 47-55
    
* Clear timer before the measurement, so that the measurement time will be measured from this point.

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 57

* Finally, start the measurement

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 58

* Read the data from the instrument buffer, parse it and convert into :class:`pandas.DataFrame` for further actions.

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 60

* Force 0 V to SMU outputs. Note, that we use it **after** reading the data to ensure that the measurement is finished and all the data is read from the instrument buffer.

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 61

  Alternatively, you can use :meth:`check_idle <probe_station.measurements.b1500.B1500.check_idle>` method to wait for the measurement to finish before reading the data.

  .. code-block:: python
    
    b1500.send_trigger()
    b1500.check_idle()
    b1500.force_gnd()

    b1500.read_data()

  .. TODO: Проверь, что так работает

* Plot the data using :mod:`matplotlib`

  .. literalinclude:: ../../../examples/iv_sweep_b1500.py
    :language: python
    :lines: 63-

Here is a full version once again

.. admonition:: DC IV sweep script
    :collapsible: closed

    .. literalinclude:: ../../../examples/iv_sweep_b1500.py
        :language: python

Measuring current from multiple channels
----------------------------------------

Sometimes, you may want to also measure current from another channel (e.g. when measuring :math:`I_{ds}(V_{ds})`, you may want to also measure gate leakage current). In this case, you can setup another SMU to measure current in parallel. For this, you need to setup the measurement mode for the second SMU

.. code-block:: diff

  - b1500.meas_mode(MeasMode.STAIRCASE_SWEEP, smu_top)
  + b1500.meas_mode(MeasMode.STAIRCASE_SWEEP, smu_top, smu_bottom)

And also configure the measurement settings for the second SMU:

.. code-block:: diff

  smu_top.meas_op_mode = MeasOpMode.CURRENT
  smu_top.meas_range_current = 0
  smu_top.adc_type = ADCType.HRADC
  
  + smu_bottom.meas_op_mode = MeasOpMode.CURRENT
  + smu_bottom.meas_range_current = 0
  + smu_bottom.adc_type = ADCType.HRADC

After that, additional columns will be present in the data, corresponding to the second SMU.

.. seealso::

    `fet_ids_vds_runner.py <https://github.com/mipt-srf/probe-station/blob/master/src/probe_station/measurements/smu/fet_ids_vds_runner.py>`__ as an example of measuring current from multiple channels in parallel

