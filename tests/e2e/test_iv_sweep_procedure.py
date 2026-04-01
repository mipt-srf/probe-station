from unittest.mock import patch

import pytest

from probe_station.measurements.voltage_sweeps.IV.SMU.built_in_procedure import IvSweepProcedure

pytestmark = pytest.mark.e2e


def test_iv_sweep_procedure():
    procedure = IvSweepProcedure()

    emitted = []
    with patch.object(procedure, "emit", side_effect=lambda *args: emitted.append(args)):
        procedure.startup()
        procedure.execute()
        procedure.shutdown()

    assert len(emitted) >= 1
    record_type, data = emitted[0]
    assert record_type == "batch results"
    assert set(data.keys()) == set(IvSweepProcedure.DATA_COLUMNS)
    assert len(data["Voltage"]) == procedure.steps
