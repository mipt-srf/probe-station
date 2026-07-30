"""Remote-Sense and Switch Unit (RSU) routing configuration."""

from enum import Enum

from keysight_b1530a._bindings.config import WGFMUChannel
from keysight_b1530a._bindings.configuration import set_operation_mode
from keysight_b1530a.enums import WGFMUOperationMode
from pymeasure.instruments.agilent.agilentB1500 import (
    AgilentB1500,
    ControlMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
)


class RSUOutputMode(Enum):
    """Output routing mode of the Remote-Sense and Switch Unit (RSU)."""

    SMU = 0
    SPGU = 1
    WGFMU = 2


class RSU:
    """A Remote-Sense and Switch Unit, wired to one WGFMU channel.

    Instantiated by :class:`~probe_station.measurements.b1500.B1500` and reachable
    as ``b1500.rsu1`` / ``b1500.rsu2``. Each unit sits on a fixed SMU/PG selector
    port and a fixed WGFMU channel, so that wiring is declared once by the
    instrument rather than chosen at every call site.
    """

    def __init__(self, parent: AgilentB1500, port: PgSelectorPort, wgfmu_channel: WGFMUChannel):
        """Bind an RSU to its selector port and WGFMU channel.

        :param parent: Connected ``AgilentB1500`` instance owning this unit.
        :param port: SMU/PG selector output port feeding this RSU.
        :param wgfmu_channel: WGFMU channel this RSU is attached to.
        """
        self._parent = parent
        self.port = port
        self.wgfmu_channel = wgfmu_channel

    def set_output(self, mode: RSUOutputMode = RSUOutputMode.SMU) -> None:
        """Route this RSU's output to the SMU, the SPGU or the WGFMU.

        :param mode: Desired output mode (SMU, SPGU, or WGFMU).
        """
        if mode == RSUOutputMode.WGFMU:
            # The WGFMU drives the RSU directly instead of going through the
            # SMU/PG selector, so no port connection is involved here.
            set_operation_mode(mode=WGFMUOperationMode.FASTIV, channel=self.wgfmu_channel)
            return

        if self._parent.io_control_mode != ControlMode.SMU_PGU_SELECTOR:
            self._parent.io_control_mode = ControlMode.SMU_PGU_SELECTOR
        status = PgSelectorConnectionStatus.SMU_ON if mode == RSUOutputMode.SMU else PgSelectorConnectionStatus.PGU_ON
        self._parent.set_port_connection(port=self.port, status=status)
        # SMU and SPGU reach the output through the WGFMU channel's pass-through.
        set_operation_mode(mode=WGFMUOperationMode.SMU, channel=self.wgfmu_channel)
