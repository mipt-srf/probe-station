############
Installation
############

How to install the package depends on what you're going to do with it:

* :ref:`run measurements <getting-started/installation:Measurements and GUI>` - the instrument dependencies are installed as well, and the environment lives on the PC that is connected to the probe station;
* :ref:`process the data <getting-started/installation:Data processing>` that was already measured - the package is added as a dependency to the project where the processing happens;
* :doc:`develop the package <../contribution>` itself - the repository is cloned together with its :ref:`sibling checkouts <contribution:local sources>`, which is described on the :doc:`Contribution <../contribution>` page.

The commands below use `uv <https://docs.astral.sh/uv/getting-started/installation/>`__, which creates the virtual environment, installs the required Python version into it and resolves the dependencies by itself. Everything can be done with ``pip`` instead, but then the environment and the Python version are your responsibility.

Requirements
============

* **Python 3.12 or newer.** You don't need to install it yourself: ``uv`` downloads the interpreter declared in :file:`pyproject.toml` when it creates the environment.
* **Windows PC for measurements.** The WGFMU functionality is based on a compiled library that is shipped only for Windows (see :ref:`keysight-b1530a <learning-package/dependencies:keysight-b1530a>`), and the connection to the instrument is established through Keysight IO Libraries Suite. Data processing has no such restriction and works on any platform.
* **Keysight IO Libraries Suite for measurements.** It provides both the VISA implementation used to talk to the mainframe and the Connection Expert where the Remote USB interface is configured, see :doc:`Connection <../explanation/connection>` page.

The package itself is split accordingly: the base installation brings only the data processing dependencies (NumPy, pandas, Matplotlib, SciPy), while the instrument drivers are pulled in by the ``measurements`` extra.

.. note::

    The package is not published on PyPI, so it's installed from the repository. In every command below, ``probe-station @ git+https://github.com/mipt-srf/probe-station.git`` is the way to spell "the current ``master``"; to pin a particular state, append a reference to it, e.g. ``...probe-station.git@v0.1.0``.

Measurements and GUI
====================

To run the measurements, the ``measurements`` extra is needed on top of the base package. Pick the scenario that matches where you want the environment to live:

.. tab-set::

    .. tab-item:: Separate folder

        The simplest option for the PC at the probe station: an empty folder with an environment that contains nothing but the package.

        .. code-block:: console

            uv venv
            uv pip install --no-sources "probe-station[measurements] @ git+https://github.com/mipt-srf/probe-station.git"
            uv run --no-sources probe-station

    .. tab-item:: Repository clone

        Useful when you also want the examples, the tests and the sources at hand, but don't plan to change the dependencies.

        .. code-block:: console

            git clone https://github.com/mipt-srf/probe-station
            cd probe-station
            uv sync --no-sources
            uv run --no-sources probe-station

    .. tab-item:: Existing project

        When the measurements are run from a project you already have, e.g. the one where the results are processed afterwards.

        .. code-block:: console

            uv add "probe-station[measurements] @ git+https://github.com/mipt-srf/probe-station.git"
            uv run --no-sources probe-station

.. note::

    ``--no-sources`` makes ``uv`` install the dependencies from the Git URLs declared in ``[project]`` section. Without it, a clone of the repository resolves :file:`pyproject.toml` :ref:`local sources <contribution:local sources>` instead and expects the sibling checkouts of Pymeasure, ``keysight-b1530a`` and ``waveform-generator`` next to it - which is what a developer wants, and a user doesn't.

The last command in each of the scenarios starts the :ref:`launcher <learning-package/structure:Launcher>`, so it doubles as a check that the installation succeeded. Other ways to run it, as well as the overview of the available measurements, are described on the :doc:`Usage <usage>` page.

Data processing
===============

Add the package to the project where you analyze the results:

.. code-block:: console

    uv add "probe-station @ git+https://github.com/mipt-srf/probe-station.git"

If you don't have a ``uv`` project and just want the package in an environment, install it directly:

.. code-block:: console

    uv pip install "probe-station @ git+https://github.com/mipt-srf/probe-station.git"

Without the extra, this is enough for everything described in :ref:`Data processing <getting-started/usage:data processing>` section - reading the datafiles, plotting them and extracting characteristics. The measurement dependencies are not installed, so the package stays lightweight and platform-independent.

Checking the installation
=========================

Data processing is available if the package imports and reports the installed version:

.. code-block:: console

    (.venv) python -c "from importlib.metadata import version; print(version('probe-station'))"

.. note:: Presence of ``(.venv)`` indicates that the command must be executed in the virtual environment with the installed package. With ``uv``, prepend ``uv run`` to the command instead of activating the environment.

Measurements additionally need the instrument to answer. The connection is checked without running anything on it, by connecting and asking the mainframe to identify itself:

.. code-block:: python

    >>> from probe_station import connect_instrument
    >>> inst = connect_instrument()
    >>> inst.id  # identification string of the mainframe

:func:`~probe_station.measurements.b1500_helpers.connect_instrument` raises :exc:`ConnectionError` when the instrument doesn't answer. In this case the package itself is installed correctly, but the instrument is not reachable - see :doc:`Connection <../explanation/connection>` page for how the connection is set up and which address is used by default.

.. seealso::

    :doc:`usage`
        what the package can be used for once it's installed

    :doc:`../tutorial/writing-your-first-script`
        the first measurement script, explained line by line

    :doc:`../contribution`
        the setup for changing the package itself, with the local checkouts of the dependencies
