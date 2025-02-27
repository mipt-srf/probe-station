Installation in editable mode
=============================

In case you would like to just use the package for your project, but still want to have an option to change something in source code, you can as well install it in editable mode. The only change is that you don't need to create separate venv, use existing one.

.. code-block:: console

    $ git clone https://github.com/mipt-srf/probe-station

.. tab-set::

    .. tab-item:: pip

        .. code-block:: console

            (.venv) $ pip install -e probe_station

    .. tab-item:: uv

        .. code-block:: console

            $ uv add --editable ./probe_station