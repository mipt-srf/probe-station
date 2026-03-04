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
from keysight_b1530a.enums import WGFMUMeasureEvent
from pymeasure.instruments.agilent.agilentB1500 import AgilentB1500


class B1500(AgilentB1500):
    """Subclass of the AgilentB1500 to add WGFMU support and some custom methods."""

    def __init__(self, adapter, **kwargs):
        super().__init__(adapter, **kwargs)
        self._wgfmu_session_opened = False
        self.initialize_all_smus()
        self.initialize_all_spgus()
        self.initialize_cmu()
        self._init_wgfmu_channels()

    def _init_wgfmu_channels(self):
        """Initialize the WGFMU channels."""
        self.open_wgfmu_session()
        channel_ids = self.query_wgfmu_channels()
        self.wgfmus = {}
        for i, channel_id in enumerate(channel_ids, start=1):
            wgfmu = WGFMU(id=channel_id)
            setattr(self, f"wgfmu{i}", wgfmu)
            self.wgfmus[i] = wgfmu

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
        """Query the available WGFMU channel IDs."""
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
