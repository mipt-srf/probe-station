import threading
from functools import wraps

from keysight_b1530a import (
    WGFMU,
    add_vector,
    add_vectors,
    clear,
    close_session,
    create_pattern,
    execute,
    get_channel_ids,
    initialize,
    open_session,
    set_measure_event,
    wait_until_completed,
)
from keysight_b1530a._bindings.config import WGFMUChannel
from keysight_b1530a.enums import (
    WGFMUMeasureCurrentRange,
    WGFMUMeasureEvent,
    WGFMUMeasureMode,
    WGFMUOperationMode,
)
from pymeasure.instruments.agilent.agilentB1500 import (
    SMU,
    SPGU,
    ADCMode,
    ADCType,
    AgilentB1500,
    AutoManual,
    CompliancePolarity,
    ControlMode,
    MeasMode,
    MeasOpMode,
    MFCMUMeasurementMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
    SamplingMode,
    SamplingPostOutput,
    SCUUPath,
    SPGUChannel,
    SPGUChannelOutputMode,
    SPGUOperationMode,
    SPGUOutputMode,
    SPGUSignalSource,
    StaircaseSweepPostOutput,
    SweepMode,
    WaitTimeType,
)

from probe_station.measurements.rsu import RSU, RSUOutputMode

# Instrument enums and channel classes are re-exported here so measurement
# scripts can import them alongside B1500 without knowing which upstream
# package each one lives in.
__all__ = [
    "B1500",
    "RSU",
    "SMU",
    "SPGU",
    "ADCMode",
    "ADCType",
    "AutoManual",
    "CompliancePolarity",
    "ControlMode",
    "MFCMUMeasurementMode",
    "MeasMode",
    "MeasOpMode",
    "PgSelectorConnectionStatus",
    "PgSelectorPort",
    "RSUOutputMode",
    "SCUUPath",
    "SPGUChannel",
    "SPGUChannelOutputMode",
    "SPGUOperationMode",
    "SPGUOutputMode",
    "SPGUSignalSource",
    "SamplingMode",
    "SamplingPostOutput",
    "StaircaseSweepPostOutput",
    "SweepMode",
    "WGFMUMeasureCurrentRange",
    "WGFMUMeasureEvent",
    "WGFMUMeasureMode",
    "WGFMUOperationMode",
    "WaitTimeType",
]


def _synchronized(method):
    """Serialize a VISA I/O method on the instrument's re-entrant ``_io_lock``.

    The B1500 owns a single shared connection (one instance per process; see
    :class:`~probe_station.measurements.session.Session`). Concurrent worker
    threads must never interleave traffic on it, or one thread's reply splices
    into another's -- e.g. a liveness-probe ``*IDN?`` response landing in the
    middle of a running sweep's data stream. Holding the lock per call makes
    each transaction atomic; the lock is re-entrant so compound calls
    (``ask`` = write + read) nest, and so :meth:`B1500.iter_output` can hold it
    across an entire sweep while still issuing reads underneath.
    """

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._io_lock:
            return method(self, *args, **kwargs)

    return wrapper


class B1500(AgilentB1500):
    """Subclass of the AgilentB1500 to add WGFMU support and some custom methods."""

    def __init__(self, adapter="USB1::0x0957::0x0001::0001::0::INSTR", **kwargs):
        # Created before super().__init__(), which already drives I/O through
        # the synchronized methods below.
        self._io_lock = threading.RLock()
        super().__init__(adapter, **kwargs)
        self._wgfmu_session_opened = False
        self.initialize_all_smus()
        self.initialize_all_spgus()
        self.initialize_cmu()
        self._init_wgfmu_channels()
        self._init_rsus()

    # --- Serialized VISA I/O ------------------------------------------------
    # Every entry point that touches the shared connection takes _io_lock so
    # concurrent threads never interleave traffic. These four cover all paths:
    # ``ask`` for queries and property reads, ``write`` for commands and
    # property writes, ``read``/``read_bytes`` for the parent's data reads
    # (read_data/read_channels) and our iter_output stream.

    @_synchronized
    def write(self, command, **kwargs):
        return super().write(command, **kwargs)

    @_synchronized
    def read(self, **kwargs):
        return super().read(**kwargs)

    @_synchronized
    def read_bytes(self, count, **kwargs):
        return super().read_bytes(count, **kwargs)

    @_synchronized
    def ask(self, command, query_delay=None):
        return super().ask(command, query_delay)

    def _init_wgfmu_channels(self):
        """Initialize the WGFMU channels."""
        self.open_wgfmu_session()
        channel_ids = self.query_wgfmu_channels()
        self.wgfmus: dict[int, WGFMU] = {}
        for i, channel_id in enumerate(channel_ids, start=1):
            wgfmu = WGFMU(id=channel_id)
            setattr(self, f"wgfmu{i}", wgfmu)
            self.wgfmus[i] = wgfmu

    def _init_rsus(self):
        """Create the RSUs, accessible as ``rsu1``/``rsu2``.

        Unlike SMUs, SPGUs and the CMU, an RSU is an external accessory that
        ``query_modules`` cannot discover, so its wiring -- which selector port
        feeds it and which WGFMU channel it hangs off -- is declared here.
        """
        wiring = (
            (PgSelectorPort.OUTPUT_1_FIRST, WGFMUChannel.CH2),
            (PgSelectorPort.OUTPUT_2_FIRST, WGFMUChannel.CH1),
        )
        self.rsus: dict[int, RSU] = {}
        for i, (port, channel) in enumerate(wiring, start=1):
            rsu = RSU(self, port=port, wgfmu_channel=channel)
            setattr(self, f"rsu{i}", rsu)
            self.rsus[i] = rsu

    def open_wgfmu_session(self):
        """Open a session to the WGFMU module."""
        if not self._wgfmu_session_opened:
            open_session(self.adapter.resource_name)
            self._wgfmu_session_opened = True

    def close_wgfmu_session(self):
        """Close the session to the WGFMU module."""
        if self._wgfmu_session_opened:
            close_session()  # Note: will cause the error if the session was closed already from outside
            self._wgfmu_session_opened = False

    @wraps(get_channel_ids)
    def query_wgfmu_channels(self):
        return get_channel_ids()

    @wraps(execute)
    def run_wgfmu_measurement(self):
        execute()
        wait_until_completed()

    @wraps(create_pattern)
    def create_wgfmu_pattern(self, name: str, start_voltage: float):
        return create_pattern(name, start_voltage)

    @wraps(add_vector)
    def add_vector_to_wgfmu_pattern(self, pattern_name: str, voltage: float, duration: float):
        add_vector(pattern_name, voltage, duration)

    @wraps(add_vectors)
    def add_vectors_to_wgfmu_pattern(self, pattern_name: str, voltages: list[float], durations: list[float]):
        add_vectors(pattern_name, voltages, durations)

    @wraps(set_measure_event)
    def set_wgfmu_measure_event(
        self,
        pattern_name: str,
        event_name: str,
        points: int,
        interval: float,
        average: float,
        mode: WGFMUMeasureEvent = WGFMUMeasureEvent.AVERAGED,
        start_time: float = 0.0,
    ):
        set_measure_event(pattern_name, event_name, points, interval, average, mode, start_time)

    @wraps(initialize)
    def initialize_wgfmu(self):
        initialize()

    @wraps(clear)
    def clear_wgfmu(self):
        clear()

    # --- Data reading -------------------------------------------------------
    # Every value is decoded by the formatting class pymeasure installs in
    # ``data_format``, so all implemented formats work: the ASCII formats
    # (1, 11, 21) and the 8 byte binary format 14.

    def _require_data_format(self):
        """Return the active data formatting class, or raise if none is set."""
        if self._data_format is None:
            raise ValueError("No data format set. Call data_format() before reading data.")
        return self._data_format

    def _value_reader(self, data_format):
        """Return a callable that reads and decodes one measurement value.

        Reads are sized per value instead of waiting for end-of-message (EOM),
        which is what enables the real-time per-step readout of
        :meth:`iter_records`.
        """
        resource = self.adapter.connection

        if data_format.binary:
            size = data_format.size

            def next_record():
                # break_on_termchar must stay off: a binary value is a fixed
                # number of bytes and may carry a termination character as
                # payload, so only the byte count delimits it.
                return data_format.format_single(resource.read_bytes(size))

            return next_record

        buf = bytearray()

        def next_record():
            while True:
                for i, byte in enumerate(buf):
                    if byte in (ord(","), ord("\r"), ord("\n")):
                        token = buf[:i].decode("ascii")
                        del buf[: i + 1]
                        if token:
                            return data_format.format_single(token)
                        break  # empty token (e.g. \n after \r), keep scanning
                buf.extend(resource.read_bytes(16, break_on_termchar=True))

        return next_record

    def iter_records(self, total_steps: int, values_per_step: int):
        """Read sweep output step-by-step (B1500 guide section 1-19).

        Yields tuples of `values_per_step` ``(status, channel, data_name, value)``
        records, one tuple per sweep step. Call after send_trigger() has been
        issued. Use :meth:`iter_output` when only the values are needed.

        The data names identify the returned quantities, which matters for the
        MFCMU: the ``IMP`` command has no effect under the binary format 14, so
        the instrument reports resistance/reactance or conductance/susceptance
        regardless of the requested measurement mode.
        """
        next_record = self._value_reader(self._require_data_format())

        # Hold the I/O lock for the whole sweep so nothing else (e.g. a Session
        # liveness probe issuing *IDN?) can interleave traffic on the shared
        # connection mid-stream. Released when the generator is exhausted,
        # closed (procedure returns early on stop), or raises.
        with self._io_lock:
            for _ in range(total_steps):
                yield tuple(next_record() for _ in range(values_per_step))

    def iter_output(self, total_steps: int, values_per_step: int):
        """Read sweep output step-by-step as plain floats.

        Yields tuples of `values_per_step` floats, one tuple per sweep step.
        Call after send_trigger() has been issued.
        """
        for records in self.iter_records(total_steps, values_per_step):
            yield tuple(value for *_, value in records)

    def read_values(self, count: int) -> list[float]:
        """Read `count` measurement values from the output buffer as floats.

        :param count: Number of values (measurement channels and sweep sources,
            depending on the data output settings) of one measurement point.
        """
        return [value for *_, value in self.read_channels(count)]

    def read_all_records(self) -> list[tuple]:
        """Read the whole output buffer as ``(status, channel, data_name, value)`` records.

        Binary data carries no terminator, so the number of values in the buffer
        is queried (``NUB?``) to read the exact number of bytes; ASCII data is
        read up to its end-of-message. Wait for the measurement to finish before
        calling this, otherwise not all data is in the buffer yet.
        """
        data_format = self._require_data_format()
        if data_format.binary:
            return list(self.read_channels(self.number_of_data))
        return [data_format.format_single(element) for element in self.read().split(",")]

    def read_all_values(self) -> list[float]:
        """Read every value currently in the output buffer as floats."""
        return [value for *_, value in self.read_all_records()]
