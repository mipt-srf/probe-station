from keysight_b1530a import (
    WGFMU,
    close_session,
    get_channel_ids,
    open_session,
)
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
        self.wgfmus = []
        for channel_id in channel_ids:
            wgfmu = WGFMU(id=channel_id)
            setattr(self, f"wgfmu{channel_id}", wgfmu)
            self.wgfmus.append(wgfmu)

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

    def query_wgfmu_channels(self):
        """Query the available WGFMU channel IDs."""
        return get_channel_ids()
