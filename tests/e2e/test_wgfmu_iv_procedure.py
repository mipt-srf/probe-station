from unittest.mock import patch

import pytest

from probe_station.measurements.voltage_sweeps.IV.WGFMU.procedure import WgfmuIvSweepProcedure

pytestmark = pytest.mark.e2e


def test_wgfmu_iv_procedure():
    procedure = WgfmuIvSweepProcedure()

    emitted = []
    with patch.object(procedure, "emit", side_effect=lambda *args: emitted.append(args)):
        procedure.startup()
        procedure.execute()
        procedure.shutdown()

    assert len(emitted) >= 1
    record_type, data = emitted[0]
    assert record_type == "batch results"
    assert set(data.keys()).issubset(set(WgfmuIvSweepProcedure.DATA_COLUMNS))
