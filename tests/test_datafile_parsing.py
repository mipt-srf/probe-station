from pathlib import Path

import pytest

from probe_station import Dataset
from probe_station._CV import CV
from probe_station._DC_IV import DC_IV
from probe_station._PQ_PUND import PQ_PUND
from probe_station._PUND_double import PUND_double


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
    assert handler.transition_current_df.shape == (1200, 4)
    assert handler.plateau_current_df.shape == (1200, 4)
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


def test_PUND_double(dataset_loader):
    handler = dataset_loader("PUND_double.data").handler
    assert isinstance(handler, PUND_double)
    assert handler.measurement == 12
    assert handler.measurement_id == 739722.659465
    assert handler.first_bias == 5
    assert handler.second_bias == -5
    assert handler.repetitions == 1e4
    assert handler.pulse_width == 1e-3
    assert handler.pulse_separation == 1e-3
    assert handler.pulse_width == 1e-3
    assert handler.slope_time == 1e-3
    assert handler.charge_df.shape[0] == 1e4
