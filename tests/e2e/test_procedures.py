from unittest.mock import patch

import pytest

from probe_station.measurements.voltage_sweeps.CV.procedure import CvSweepProcedure
from probe_station.measurements.voltage_sweeps.IV.pg_with_current_measurement_procedure import PgCyclingProcedure
from probe_station.measurements.voltage_sweeps.IV.SMU.built_in_procedure import IvSweepProcedure
from probe_station.measurements.voltage_sweeps.IV.WGFMU.procedure import WgfmuIvSweepProcedure

pytestmark = pytest.mark.e2e


def run_procedure(procedure):
    """Run procedure lifecycle and return emitted data without a Qt application or pymeasure Worker."""
    emitted = []
    with (
        patch.object(procedure, "emit", side_effect=lambda *args: emitted.append(args)),
        patch.object(procedure, "should_stop", return_value=False),
    ):
        procedure.startup()
        procedure.execute()
        procedure.shutdown()
        procedure.b1500.close_wgfmu_session()
    return emitted


def test_iv_sweep_procedure():
    procedure = IvSweepProcedure()
    emitted = run_procedure(procedure)

    results = [(record_type, data) for record_type, data in emitted if record_type == "results"]
    assert len(results) == 2 * procedure.steps
    _, data = results[0]
    assert set(data.keys()) == set(IvSweepProcedure.DATA_COLUMNS)


def test_cv_procedure():
    procedure = CvSweepProcedure()
    emitted = run_procedure(procedure)

    results = [(record_type, data) for record_type, data in emitted if record_type == "results"]
    assert len(results) > 0
    _, data = results[0]
    assert set(data.keys()) == set(CvSweepProcedure.DATA_COLUMNS)


def test_wgfmu_iv_procedure():
    procedure = WgfmuIvSweepProcedure()
    emitted = run_procedure(procedure)

    assert len(emitted) >= 1
    record_type, data = emitted[0]
    assert record_type == "batch results"
    assert set(data.keys()).issubset(set(WgfmuIvSweepProcedure.DATA_COLUMNS))


def test_pg_iv_procedure():
    procedure = PgCyclingProcedure()
    emitted = run_procedure(procedure)

    results = [(record_type, data) for record_type, data in emitted if record_type == "results"]
    assert len(results) > 0
    _, data = results[0]
    assert set(data.keys()) == set(PgCyclingProcedure.DATA_COLUMNS)
