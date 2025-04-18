from pathlib import Path

import pytest

from probe_station import Dataset
from probe_station._CV import CV
from probe_station._DC_IV import DC_IV
from probe_station._PQ_PUND import PQ_PUND


@pytest.fixture
def dataset_loader():
    def _load(filename):
        pq_pund_file = Path(__file__).parent / "data" / filename
        return Dataset(pq_pund_file)

    return _load


def test_PQ_PUND(dataset_loader):
    handler = dataset_loader("PQ_PUND.data").handler
    assert isinstance(handler, PQ_PUND)
    assert handler.measurement == 10
    assert handler.measurement_id == 739722.655036
    assert handler.first_bias == 5
    assert handler.second_bias == -5
    assert handler.steps == 121
    assert handler.repetitions == 5
    assert handler.rump_time == 1e-5
    assert handler.rump_integration_time == 5e-6
    assert handler.wait_time == 1e-5
    assert handler.wait_integration_time == 5e-6
    assert handler.current_df.shape == (1200, 4)
    assert handler.leakage_df.shape == (1200, 3)
    assert handler.qv_df.shape == (1200, 2)


def test_DC_IV(dataset_loader):
    handler = dataset_loader("DC_IV.data").handler
    assert isinstance(handler, DC_IV)
    assert handler.measurement == 4
    assert handler.measurement_id == 739722.647152
    assert handler.series_id == 0
    assert handler.mode == 2
    assert handler.first_bias == -3
    assert handler.second_bias == 3
    assert handler.step == 0.05
    assert handler.pos_compliance == 0.1
    assert handler.neg_compliance == 0.1
    assert handler.steps == handler.data.shape[0]


def test_CV(dataset_loader):
    handler = dataset_loader("CV.data").handler
    assert isinstance(handler, CV)
    assert handler.measurement == 5
    assert handler.measurement_id == 739587.531070
    assert handler.series_id == 0
    assert handler.mode == 1
    assert handler.first_bias == -4.5
    assert handler.second_bias == 4.3
    assert handler.step == 0.05
    assert handler.sweep_mode == 3
    assert handler.frequency == 1e5
    assert handler.steps == handler.data.shape[0]
