"""Offline tests of the format-agnostic B1500 data reading paths.

The instrument is replaced by a fake VISA resource replaying a recorded byte
stream, so the ASCII (FMT1, FMT21) and binary (FMT14) decoding can be checked
without hardware.
"""

import math
import threading
from types import SimpleNamespace

import pytest
from pymeasure.instruments.agilent.agilentB1500 import AgilentB1500

from probe_station.measurements.b1500 import B1500
from probe_station.measurements.b1500_helpers import to_cp_rp

UNIT_NAMES = {1: "SMU1", 2: "SMU2", 3: "SMU3", 4: "SMU4", 5: "CMU1"}

# One sweep of two steps, each (time, measured current, forced voltage).
EXPECTED_STEPS = [(0.5, 2.5e-05, 2.0), (1.0, -1.25e-05, -1.0)]


class FakeResource:
    """Minimal stand-in for the pyvisa resource behind the adapter."""

    def __init__(self, payload: bytes):
        self.payload = payload
        self.pos = 0

    def read_bytes(self, count, break_on_termchar=False):
        chunk = self.payload[self.pos : self.pos + count]
        if break_on_termchar:
            for i, byte in enumerate(chunk):
                if byte in (ord("\r"), ord("\n")):
                    chunk = chunk[: i + 1]
                    break
        if not chunk:
            raise EOFError("fake resource exhausted")
        self.pos += len(chunk)
        return chunk


def fake_b1500(payload: bytes, data_format) -> B1500:
    """Build a B1500 that reads *payload* instead of talking to an instrument."""
    b1500 = object.__new__(B1500)  # __init__ would open a VISA and WGFMU session
    b1500._io_lock = threading.RLock()
    b1500._data_format = data_format
    b1500.adapter = SimpleNamespace(connection=FakeResource(payload))
    return b1500


def fmt14_measurement(parameter, range_code, count, channel, status=0):
    """Build one 8 byte FMT14 element (A=1, measurement data)."""
    head = 0x80 | parameter
    return bytes([head, range_code]) + count.to_bytes(4, "big", signed=True) + bytes([status, channel])


def fmt14_source(parameter, range_code, count, channel, status=0):
    """Build one 8 byte FMT14 element (A=0, source data)."""
    return bytes([parameter, range_code]) + count.to_bytes(4, "big", signed=True) + bytes([status, channel])


def fmt14_time(seconds):
    """Build one 8 byte FMT14 time element (6 byte count, no range or status)."""
    return bytes([0x03]) + int(seconds * 1e6).to_bytes(6, "big", signed=True) + bytes([0])


# Range 16 = 1e-4 A, range 12 = 20 V; the value is count * range / 1e6.
FMT14_PAYLOAD = b"".join(
    [
        fmt14_time(0.5),
        fmt14_measurement(1, 16, 250_000, 4),
        fmt14_source(0, 12, 100_000, 4),
        fmt14_time(1.0),
        fmt14_measurement(1, 16, -125_000, 4),
        fmt14_source(0, 12, -50_000, 4),
    ]
)
# Channel letter D is slot 4, matching the channel number of the binary payload.
FMT1_PAYLOAD = b"NDT+5.00000E-01,NDI+2.50000E-05,NDV+2.00000E+00,NDT+1.00000E+00,NDI-1.25000E-05,NDV-1.00000E+00\r\n"
FMT21_PAYLOAD = (
    b"000DT+5.00000E-01,000DI+2.50000E-05,000Dv+2.00000E+00,000DT+1.00000E+00,000DI-1.25000E-05,000Dv-1.00000E+00\r\n"
)


FORMATTERS = {
    "FMT1": AgilentB1500._data_formatting_FMT1,
    "FMT21": AgilentB1500._data_formatting_FMT21,
    "FMT14": AgilentB1500._data_formatting_FMT14,
}
PAYLOADS = {"FMT1": FMT1_PAYLOAD, "FMT21": FMT21_PAYLOAD, "FMT14": FMT14_PAYLOAD}


def formatter(name):
    return FORMATTERS[name](unit_names=UNIT_NAMES)


@pytest.mark.parametrize("format_name", list(PAYLOADS))
def test_iter_output_decodes_every_format(format_name):
    b1500 = fake_b1500(PAYLOADS[format_name], formatter(format_name))
    assert list(b1500.iter_output(2, 3)) == EXPECTED_STEPS


@pytest.mark.parametrize("format_name", list(PAYLOADS))
def test_iter_records_reports_channels_and_names(format_name):
    b1500 = fake_b1500(PAYLOADS[format_name], formatter(format_name))
    first_step = next(iter(b1500.iter_records(2, 3)))
    names = [record[2] for record in first_step]
    assert names[0] == "Time (s)"
    assert names[1].startswith("Current")
    assert names[2].startswith("Voltage")
    assert [record[1] for record in first_step[1:]] == ["SMU4", "SMU4"]


def test_read_all_values_binary_uses_buffer_count(monkeypatch):
    b1500 = fake_b1500(FMT14_PAYLOAD, formatter("FMT14"))
    monkeypatch.setattr(B1500, "number_of_data", property(lambda self: 6))
    monkeypatch.setattr(B1500, "read_bytes", lambda self, count, **kw: self.adapter.connection.read_bytes(count))
    assert b1500.read_all_values() == [value for step in EXPECTED_STEPS for value in step]


def test_read_all_values_ascii_reads_to_end_of_message(monkeypatch):
    b1500 = fake_b1500(FMT1_PAYLOAD, formatter("FMT1"))
    monkeypatch.setattr(B1500, "read", lambda self, **kw: FMT1_PAYLOAD.decode().strip())
    assert b1500.read_all_values() == [value for step in EXPECTED_STEPS for value in step]


def test_read_values_reads_one_point(monkeypatch):
    b1500 = fake_b1500(FMT14_PAYLOAD, formatter("FMT14"))
    monkeypatch.setattr(B1500, "read_bytes", lambda self, count, **kw: self.adapter.connection.read_bytes(count))
    assert b1500.read_values(3) == list(EXPECTED_STEPS[0])


class TestToCpRp:
    """1 nF in parallel with 1 MOhm at 10 kHz, expressed in every pair the CMU may return."""

    frequency = 1e4
    cp = 1e-9
    rp = 1e6

    def records(self, first_name, first, second_name, second):
        return (("", "CMU1", first_name, first), ("", "CMU1", second_name, second))

    def test_impedance_pair(self):
        admittance = complex(1 / self.rp, 2 * math.pi * self.frequency * self.cp)
        impedance = 1 / admittance
        cp, rp = to_cp_rp(
            self.records("Resistance (Ohm)", impedance.real, "Reactance (Ohm)", impedance.imag),
            self.frequency,
        )
        assert cp == pytest.approx(self.cp)
        assert rp == pytest.approx(self.rp)

    def test_admittance_pair(self):
        cp, rp = to_cp_rp(
            self.records(
                "Conductance (S)",
                1 / self.rp,
                "Susceptance (S)",
                2 * math.pi * self.frequency * self.cp,
            ),
            self.frequency,
        )
        assert cp == pytest.approx(self.cp)
        assert rp == pytest.approx(self.rp)

    def test_capacitance_pair_passes_through(self):
        # ASCII formats honour IMP, so the requested Cp/Rp pair is returned as is.
        assert to_cp_rp(self.records("Capacitance (F)", self.cp, "Phase (rad)", self.rp), self.frequency) == (
            self.cp,
            self.rp,
        )

    def test_singular_impedance_is_nan(self):
        cp, rp = to_cp_rp(self.records("Resistance (Ohm)", 0.0, "Reactance (Ohm)", 0.0), self.frequency)
        assert math.isnan(cp)
        assert math.isnan(rp)
