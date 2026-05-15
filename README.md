# Probe Station

Draft command reference for installing, testing, and developing the package.

## CI Checks

CI should test the package as a consumer would install it: ignore local uv source
overrides, install the package and test dependencies, and skip hardware tests.

```bash
uv venv --python 3.12
uv pip install --no-sources -e ".[tests]"
uv run --no-sync python -m pytest --ignore=tests/e2e
```

To also verify measurement dependencies can be installed from their declared
GitHub sources:

```bash
uv pip install --no-sources -e ".[measurements,tests]"
uv run --no-sync python -m pytest --ignore=tests/e2e
```

## Measurement Development

Use local editable sources when developing `probe-station` together with related
packages.

Expected sibling checkout layout:

```text
Repositories/
  probe-station/
  pymeasure/
  keysight-b1530a/
  waveform-generator/
```

Then run from `probe-station`:

```bash
uv sync --extra measurements
uv run python -m pytest --ignore=tests/e2e
```

When connected to the instrument, run hardware tests explicitly:

```bash
uv run python -m pytest tests/e2e
```

## Data Processing Usage

For data processing in another project:

```bash
uv add "probe-station @ git+https://github.com/mipt-srf/probe-station.git"
```

Or with `uv pip`:

```bash
uv pip install "probe-station @ git+https://github.com/mipt-srf/probe-station.git"
```

For measurement and GUI usage:

```bash
uv add "probe-station[measurements] @ git+https://github.com/mipt-srf/probe-station.git"
```
