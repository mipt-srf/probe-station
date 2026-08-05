"""Quick-start action: reset instrument, configure RSUs, set SMU compliances."""

import logging

from probe_station.measurements.b1500 import RSUOutputMode
from probe_station.measurements.b1500_helpers import set_smu_compliances  # enable_all_smus
from probe_station.measurements.session import Session

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def run() -> None:
    """Force-reset the B1500 and configure RSU routing + SMU compliances.

    Uses :meth:`Session.reconnect` so the launcher process picks up the
    fresh handle; the singleton owns lifetime, so no per-call close is
    needed.
    """
    b1500 = Session.reconnect(reset=True)
    b1500.rsu1.set_output(RSUOutputMode.SMU)
    b1500.rsu2.set_output(RSUOutputMode.SMU)
    set_smu_compliances(b1500, current_comp=0.1)
    # enable_all_smus(b1500)


if __name__ == "__main__":
    run()
