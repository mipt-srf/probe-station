from unittest.mock import patch

import pytest

from probe_station.measurements.voltage_sweeps.CV.procedure import CvSweepProcedure

pytestmark = pytest.mark.e2e


def test_cv_procedure():
    procedure = CvSweepProcedure()

    emitted = []
    with patch.object(procedure, "emit", side_effect=lambda *args: emitted.append(args)):
        procedure.startup()
        procedure.execute()
        procedure.shutdown()

    results = [(record_type, data) for record_type, data in emitted if record_type == "results"]
    assert len(results) > 0
    _, data = results[0]
    assert set(data.keys()) == set(CvSweepProcedure.DATA_COLUMNS)
