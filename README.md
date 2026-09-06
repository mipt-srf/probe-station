# Probe Station

[![Documentation](https://readthedocs.org/projects/probe-station/badge/?version=latest)](https://probe-station.readthedocs.io)
[![CI](https://github.com/mipt-srf/probe-station/actions/workflows/ci.yaml/badge.svg)](https://github.com/mipt-srf/probe-station/actions/workflows/ci.yaml)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)

Python package for running measurements on a **Keysight B1500** semiconductor parameter
analyzer and processing their results. Developed at the Shared Research Facilities (SRF)
Center of the Moscow Institute of Physics and Technology (MIPT).

The package replaces hand-written [FLEX](https://probe-station.readthedocs.io/en/latest/explanation/b1500-specifics.html)
command strings sent over VISA with a Python interface, ships ready-to-run GUIs for
the common measurements, and provides handlers that turn the resulting datafiles into
`pandas` frames, plots and extracted characteristics.

📖 **[Full documentation](https://probe-station.readthedocs.io)**

## What you can do with it

- **Run measurements from a GUI** — IV, CV, cycling and FET characteristics, each with its
  own parameter window, live plot and CSV output.
- **Write measurement scripts** — drive SMU, CMU, SPGU and WGFMU units through the
  [`B1500`](https://probe-station.readthedocs.io/en/latest/learning-package/b1500-class.html)
  class instead of raw FLEX commands.
- **Process the data** — load result files, plot them and extract characteristics
  (coercive voltage and dielectric constant from CV, polarization from IV) with
  procedure-specific handlers.

Data processing needs nothing but the base install and works on any platform. Measurements
require Windows, Keysight IO Libraries Suite and the `measurements` extra.

## Installation

The package is not on PyPI, so it is installed from this repository. The commands below use
[uv](https://docs.astral.sh/uv/getting-started/installation/), which creates the environment
and fetches Python 3.12 on its own.

**Measurements and GUI** (on the PC connected to the probe station):

```bash
uv venv
uv pip install --no-sources "probe-station[measurements] @ git+https://github.com/mipt-srf/probe-station.git"
uv run --no-sources probe-station
```

**Data processing** (in the project where you analyze the results):

```bash
uv add "probe-station @ git+https://github.com/mipt-srf/probe-station.git"
```

Other scenarios — a clone of the repository, an existing project, installing without `uv` —
are covered on the [Installation](https://probe-station.readthedocs.io/en/latest/getting-started/installation.html)
page.

## Quick start

Launch the GUI with the measurement buttons:

```bash
probe-station
```

Talk to the instrument from a script:

```python
from probe_station import B1500

inst = B1500()
inst.smu4.enable()
```

Read and plot a measured datafile:

```python
from probe_station import Dataset

ds = Dataset("example_cv.csv")
ds.data                             # pandas.DataFrame with the measured columns
ds.parameters                       # parameters the measurement was run with
ds.plot()                           # procedure-specific plot
ds.handler.get_coercive_voltage()   # handler methods depend on the procedure
```

See the [Usage](https://probe-station.readthedocs.io/en/latest/getting-started/usage.html)
page for the walkthrough of all three modes.

## Available measurements

| Measurement | Unit | Module |
| --- | --- | --- |
| IV sweep | SMU | `measurements.smu.iv_sweep` |
| Fast IV sweep | WGFMU | `measurements.wgfmu.iv_sweep` |
| IV sweep (experimental) | SPGU | `measurements.spgu.cycling_with_current` |
| Cycling | WGFMU | `measurements.wgfmu.cycling` |
| Cycling | SPGU | `measurements.spgu.cycling` |
| CV sweep | CMU | `measurements.cmu.cv_sweep` |
| Quasi-static CV sweep (experimental) | SMU | `measurements.smu.quasistatic_cv` |
| Ids(Vg) | SMU | `measurements.smu.fet_ids_vg` |
| Ids(Vds) | SMU | `measurements.smu.fet_ids_vds` |
| Ids(Vg) | WGFMU | `measurements.wgfmu.fet_ids_vg` |
| Ids at DC bias (experimental) | WGFMU | `measurements.wgfmu.fet_ids_dc` |

Each of them is available both as a button in the launcher and as a module that can be run
or imported directly. Higher-level experiments built on top of these procedures (endurance,
retention, cycling series) live in `probe_station.experiments`. A separate launcher for the
Keithley 2450 is installed as the `keithley` command, and `reader` opens measured datafiles.

## Documentation

| Page | What it covers |
| --- | --- |
| [Installation](https://probe-station.readthedocs.io/en/latest/getting-started/installation.html) | every install scenario and how to verify it |
| [Usage](https://probe-station.readthedocs.io/en/latest/getting-started/usage.html) | scripts, GUI and data processing |
| [Writing your first script](https://probe-station.readthedocs.io/en/latest/tutorial/writing-your-first-script.html) | a measurement script explained line by line |
| [Structure](https://probe-station.readthedocs.io/en/latest/learning-package/structure.html) | how the package is organized |
| [Connection](https://probe-station.readthedocs.io/en/latest/explanation/connection.html) | VISA, the USB interface and instrument addresses |
| [API reference](https://probe-station.readthedocs.io/en/latest/api.html) | generated reference for all modules |

## Development

Bug reports, feature requests and pull requests are welcome. The package is developed
together with local checkouts of its instrument dependencies
([Pymeasure](https://github.com/pymeasure/pymeasure),
[keysight-b1530a](https://github.com/ilev-sergey/keysight-b1530a),
[waveform-generator](https://github.com/ilev-sergey/waveform-generator)), which `uv` expects
as sibling folders:

```bash
git clone https://github.com/mipt-srf/probe-station
cd probe-station
uv sync --extra measurements --extra tests
uv run pytest --ignore=tests/e2e
```

Tests that need a real instrument are collected in `tests/e2e` and are run explicitly at the
probe station with `uv run pytest tests/e2e`. Code is formatted and linted with
[Ruff](https://docs.astral.sh/ruff/); `uv run pre-commit install` wires it into your commits.

Pass `--no-sources` to `uv sync` if you don't have the sibling checkouts and want the
dependencies installed from their Git URLs instead.

The full setup — local sources, code style, tests, building the documentation and submitting
changes — is described on the
[Contribution](https://probe-station.readthedocs.io/en/latest/contribution.html) page.
