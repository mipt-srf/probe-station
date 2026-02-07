import logging

from keysight_b1530a._bindings.initialization import close_session, open_session

from probe_station.measurements.common import (
    RSU,
    RSUOutputMode,
    connect_instrument,
    # enable_all_smus,
    set_smu_compliances,
    setup_rsu_output,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())



if __name__ == "__main__":
    b1500 = connect_instrument(reset=True)
    open_session()
    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)
    set_smu_compliances(b1500, current_comp=0.1)
    # enable_all_smus(b1500)
    close_session()