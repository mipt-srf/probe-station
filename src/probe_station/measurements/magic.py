"""Quick-start action: reset instrument, configure RSUs, set SMU compliances."""

import logging

from probe_station.measurements.common import (
    RSU,
    RSUOutputMode,
    # enable_all_smus,
    set_smu_compliances,
    setup_rsu_output,
)
from probe_station.measurements.session import Session

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def run() -> None:
    """Force-reset the B1500 and configure RSU routing + SMU compliances.

    Uses :meth:`Session.reconnect` so the launcher process picks up the
    fresh handle; the singleton owns lifetime, so no per-call close is
    needed.
    """
    b1500 = Session.reconnect(reset=True)
    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)
    set_smu_compliances(b1500, current_comp=0.1)
    # enable_all_smus(b1500)


if __name__ == "__main__":
    run()
