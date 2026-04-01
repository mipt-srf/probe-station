from unittest.mock import patch

import pytest

from probe_station.measurements.voltage_sweeps.CV.procedure import CvSweepProcedure
from probe_station.measurements.voltage_sweeps.IV.SMU.built_in_procedure import IvSweepProcedure
from probe_station.measurements.voltage_sweeps.IV.WGFMU.procedure import WgfmuIvSweepProcedure

pytestmark = pytest.mark.e2e


def test_iv_sweep_procedure():
    procedure = IvSweepProcedure()

    emitted = []
    # patch emit to capture emitted data without a running Qt application or pymeasure Worker
    with patch.object(procedure, "emit", side_effect=lambda *args: emitted.append(args)):
        procedure.startup()
        procedure.execute()
        procedure.shutdown()

    assert len(emitted) >= 1
    record_type, data = emitted[0]
    assert record_type == "batch results"
    assert set(data.keys()) == set(IvSweepProcedure.DATA_COLUMNS)
    assert len(data["Voltage"]) == procedure.steps


def test_cv_procedure():
    procedure = CvSweepProcedure()

    emitted = []
    # patch emit to capture emitted data without a running Qt application or pymeasure Worker
    with patch.object(procedure, "emit", side_effect=lambda *args: emitted.append(args)):
        procedure.startup()
        procedure.execute()
        procedure.shutdown()

    results = [(record_type, data) for record_type, data in emitted if record_type == "results"]
    assert len(results) > 0
    _, data = results[0]
    assert set(data.keys()) == set(CvSweepProcedure.DATA_COLUMNS)


def test_wgfmu_iv_procedure():
    procedure = WgfmuIvSweepProcedure()

    emitted = []
    # patch emit to capture emitted data without a running Qt application or pymeasure Worker
    with patch.object(procedure, "emit", side_effect=lambda *args: emitted.append(args)):
        procedure.startup()
        procedure.execute()
        procedure.shutdown()

    assert len(emitted) >= 1
    record_type, data = emitted[0]
    assert record_type == "batch results"
    assert set(data.keys()).issubset(set(WgfmuIvSweepProcedure.DATA_COLUMNS))
