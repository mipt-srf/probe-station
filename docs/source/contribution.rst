############
Contribution
############

The package is developed at `mipt-srf/probe-station <https://github.com/mipt-srf/probe-station>`__, and bug reports, feature requests and pull requests are welcome. This page describes how to set up the development environment, run the tests, build this documentation and submit the changes.

.. note:: Unlike the rest of the documentation, this page assumes that you work inside a clone of the repository rather than with the package installed from GitHub. See :doc:`Installation <getting-started/installation>` page if you only want to use the package.

Development setup
=================

The project uses `uv <https://docs.astral.sh/uv/>`__ for dependency management, so the whole environment is created with a single command:

.. code-block:: console

    git clone https://github.com/mipt-srf/probe-station
    cd probe-station
    uv sync --extra measurements --extra tests

Dependencies are split into optional extras, so that you install only what you need:

* ``measurements`` - packages that are needed to talk to the instrument (`keysight-b1530a <https://github.com/ilev-sergey/keysight-b1530a>`__, `waveform-generator <https://github.com/ilev-sergey/waveform-generator>`__). Required for everything that runs a measurement, including the GUI, but not for data processing.
* ``tests`` - `pytest <https://docs.pytest.org/>`__ and coverage plugins, see `Running tests`_.
* ``docs`` - Sphinx and its extensions, see `Building documentation`_.

The ``dev`` dependency group (Ruff, pre-commit, IPython kernel) is not an extra and is installed by ``uv sync`` by default.

.. _local-sources:

Local sources
-------------

Most of the low-level work happens not in this package but in its :doc:`dependencies <learning-package/dependencies>`: FLEX commands are wrapped in Pymeasure, while the WGFMU functionality lives in ``keysight-b1530a``. To make it possible to change them and to test the changes from this package immediately, :file:`pyproject.toml` declares them as local editable checkouts:

.. code-block:: toml

    [tool.uv.sources]
    waveform-generator = { path = "../waveform-generator", editable = true }
    keysight-b1530a = { path = "../keysight-b1530a", editable = true }
    pymeasure = { path = "../pymeasure", editable = true }

So ``uv sync`` expects the sibling checkouts to be placed next to the package:

.. code-block:: text

    Repositories/
    ├── probe-station/
    ├── pymeasure/
    ├── keysight-b1530a/
    └── waveform-generator/

Since the checkouts are installed in editable mode, every edit in them is picked up by the next run without reinstallation. This way you can add a command to :class:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500` class and call it from a measurement script right away, without waiting for the change to be released or even merged.

If you don't need it, and want the dependencies to be installed from the sources declared in ``[project]`` section (a Git URL for each of them) instead, pass ``--no-sources``:

.. code-block:: console

    uv sync --no-sources

.. note:: The same flag is needed for ``uv run``, since it syncs the environment before running the command. Alternatively, use ``uv run --no-sync`` if the environment is already prepared.

Code style
==========

The code is formatted and linted with `Ruff <https://docs.astral.sh/ruff/>`__, configured in :file:`pyproject.toml` (the only notable deviation from the defaults is the line length of 120 characters):

.. code-block:: console

    uv run ruff check --fix
    uv run ruff format

Linting is also run in CI, so it's convenient to install the `pre-commit <https://pre-commit.com/>`__ hooks, which run both of the commands above for every commit, and additionally trim trailing whitespace and check the documentation with `sphinx-lint <https://github.com/sphinx-contrib/sphinx-lint>`__:

.. code-block:: console

    uv run pre-commit install

Running tests
=============

Tests are placed in :file:`tests` folder and are run with `pytest <https://docs.pytest.org/>`__:

.. code-block:: console

    uv run pytest --ignore=tests/e2e

Tests that need a real B1500 connected are collected in :file:`tests/e2e` folder and marked with ``e2e`` marker. Ignoring the folder is preferred over deselecting the marker with ``-m "not e2e"``, because it also skips the import of these modules, which may depend on functionality that is not available in every environment (e.g. on a Pymeasure branch that is not merged yet).

When you're at the probe station, run them explicitly:

.. code-block:: console

    uv run pytest tests/e2e

Each of them runs a whole procedure lifecycle on the instrument and checks the emitted results, so they are the fastest way to see that the package still works with the hardware after a refactoring.

.. _testing-pymeasure:

Testing Pymeasure
-----------------

While adding new commands to :ref:`AgilentB1500 class <learning-package/b1500-class:AgilentB1500 class>`, it's useful to run Pymeasure's own tests to make sure that the new commands don't break anything.

They don't need the instrument: Pymeasure runs the driver against an expected sequence of commands and responses (``expected_protocol``), so a broken command shows up as a mismatch in this sequence. Run them from your :ref:`local checkout <local-sources>` of Pymeasure:

.. code-block:: console

    cd ../pymeasure
    uv run pytest tests/instruments/agilent/test_agilentB1500.py

.. seealso::

    `Adding instruments <https://pymeasure.readthedocs.io/en/latest/dev/adding_instruments/index.html>`__, `Writing tests <https://pymeasure.readthedocs.io/en/latest/dev/adding_instruments/tests.html>`__
        Pymeasure guides on implementing and testing instrument commands

    :doc:`learning-package/b1500-class`
        how the B1500 driver is structured and which parts of it are worth extending

Building documentation
======================

The documentation is built with `Sphinx <https://www.sphinx-doc.org/>`__ from :file:`docs/source` folder and is published on Read the Docs automatically. To build it locally, use `sphinx-autobuild <https://github.com/sphinx-doc/sphinx-autobuild>`__, which rebuilds the pages and reloads the browser on every save:

.. code-block:: console

    uv run --extra docs sphinx-autobuild docs/source docs/build

A one-off build is done with ``sphinx-build``:

.. code-block:: console

    uv run --extra docs sphinx-build docs/source docs/build/html

.. note:: API pages are generated from the docstrings in :file:`src` folder, and some pages execute code at build time (see `Executed code`_). Since importing these modules pulls in the measurement dependencies, the build needs the package itself to be installed with ``measurements`` extra, not only the ``docs`` one. This is what Read the Docs does, as declared in :file:`.readthedocs.yaml`.

Writing pages
-------------

* Pages are written in reStructuredText and must be added to one of the toctrees in :file:`docs/source/index.rst` to appear in the sidebar.
* The structure follows `Diátaxis <https://diataxis.fr/>`__, so before adding a page, decide whether it explains **how to use** the package (tutorials and how-to guides) or **how it works** (reference and explanation pages), and place it accordingly.
* ``default_role`` is set to ``any``, so a single-backtick reference resolves to any matching target, and `intersphinx <https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html>`__ extension extends this to the documentation of Python, NumPy, SciPy, Matplotlib, pandas, Pymeasure, PyVISA and ``keysight-b1530a``. Because of this, referring to a class as :class:`~pymeasure.instruments.agilent.agilentB1500.AgilentB1500` links to the corresponding project.
* Section labels are generated automatically by `autosectionlabel <https://www.sphinx-doc.org/en/master/usage/extensions/autosectionlabel.html>`__ extension and prefixed with the document name, so sections are referenced as ``:ref:`explanation/connection:visa```.
* Markup mistakes that Sphinx renders silently instead of reporting - a role missing its closing backtick, a hyperlink missing its trailing underscore - are caught by `sphinx-lint <https://github.com/sphinx-contrib/sphinx-lint>`__, which runs as a pre-commit hook (see `Code style`_).

Executed code
-------------

Snippets that show the results of data processing are executed at build time by `jupyter-sphinx <https://jupyter-sphinx.readthedocs.io/>`__, with the working directory set to :file:`docs/source`. The data they use is stored in :file:`docs/source/data` folder, which is explicitly excluded from the ``*.csv`` rule in :file:`.gitignore`.

Submitting changes
==================

* Branches are named as ``<author>/<issue>-<short-description>``, where the issue is the identifier of the corresponding Linear issue for the SRF team, e.g. ``claude/srf-42-add-pulse-train``. External contributors can use any descriptive name.
* Commit messages start with a lowercase letter and describe the change, not the file that was touched.
* Pull request titles follow ``<issue>: <title>`` format, and both the title and the description are kept up to date after review fixes.
* CI runs Ruff and the non-hardware tests on every pull request. It installs the package the way a user would, with ``--no-sources``, so a change that works only against a :ref:`local checkout <local-sources>` of a dependency will fail there even if it passes locally:

  .. code-block:: console

      uv venv --python 3.12
      uv pip install --no-sources -e ".[tests]"
      uv run --no-sync python -m pytest --ignore=tests/e2e

* Hardware tests are not run in CI, so run them at the probe station yourself if the change touches the measurement code.
