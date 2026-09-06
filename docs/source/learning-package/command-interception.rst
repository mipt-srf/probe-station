####################
Command Interception
####################

Sometimes, you may want to track the commands that are sent to the instrument. For example, if you want to understand what happens during a complex measurement that is built from several scripts. Or, you can use it for debugging purposes.

For scripts based on this package, you can use :func:`~probe_station.logging_setup.setup_file_logging` function.

.. In parallel, a log is always written to a ``logs`` folder in the project directory itself. This one starts at script startup rather than at the moment of queuing, and is always there even if the measurement was not saved, which makes it easier to debug the problems reported by users.
.. move to logging part

.. code-block:: python

    from probe_station.logging_setup import setup_file_logging

    setup_file_logging("logs")

It saves all commands sent to the instrument into a ``logs`` folder. When a measurement is queued with *store measurement* enabled, such a folder is created inside the folder with measurement results, so that the log stays next to the data it describes. It's already used in all of existing :ref:`runners <learning-package/structure:Measurement scripts>`.

Under the hood, it sets ``DEBUG`` level logging for the :mod:`pyvisa` logger, so that all commands sent to the instrument are logged.

.. code-block:: python

    logging.getLogger("pyvisa").setLevel(logging.DEBUG)

Keysight IO
===========

Alternatively, as a more general approach that you can use for any script communicating using :ref:`VISA <explanation/connection:visa>` or :ref:`SICL <explanation/connection:physical and network layers>`, you can use `Keysight IO Monitor <https://helpfiles.keysight.com/IO_Libraries_Suite/English/IOLS_Linux/IOMonitor/Content/Welcome.htm>`__.

.. добавь скринов: Keysight IO кнопка, запуск мониторинга, запуск скрипта, появившивеся логи, опицонально их созранение
