import logging
import time

from keysight_b1530a import close_session
from matplotlib import pyplot as plt
from pymeasure.instruments.agilent.agilentB1500 import (
    SMU,
    SPGU,
    ALWGPattern,
    MeasMode,
    SPGUOperationMode,
    SPGUOutputMode,
)

from probe_station.measurements.b1500 import B1500
from probe_station.measurements.common import (
    RSU,
    RSUOutputMode,
    connect_instrument,
    setup_rsu_output,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def run(b1500: B1500, repetitions, amplitude, width, rise, tail, channel=102, bipolar=False, pulse_separation=True):
    if pulse_separation:
        delay_2nd = width
    else:
        delay_2nd = tail / 4
    # Total duration of one two-pulse sequence (used for DURATION output mode)
    period = 2 * (rise + width + tail) + delay_2nd
    period *= 1.025

    spgu: SPGU = b1500.spgu1

    pg = None
    for ch in [spgu.ch1, spgu.ch2]:
        if ch.id == channel:
            pg = ch
            break
    if pg is None:
        raise ValueError(f"Channel {channel} not found in SPGU channels.")
    pg.enabled = True

    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SPGU)

    spgu.operation_mode = SPGUOperationMode.ALWG
    if repetitions < 1e6:
        spgu.set_output_mode(mode=SPGUOutputMode.COUNT, condition=repetitions)
    else:
        spgu.set_output_mode(mode=SPGUOutputMode.DURATION, condition=period * repetitions)
    pg.load_impedance = 1e6

    peak_voltage_2 = -amplitude if bipolar else amplitude
    pattern = ALWGPattern(
        initial_voltage=0.0,
        voltages=[
            amplitude,
            0.0,  # pulse 1: ramp up, hold, ramp down
            peak_voltage_2,
            0.0,  # pulse 2: ramp up, hold, ramp down
        ],
        times=[
            rise,
            tail,
            rise,
            tail,
        ],
    )
    pg.set_alwg_pattern([pattern])
    spgu.set_alwg_sequence([(0, 1)])

    pg.apply_setup()

    smu: SMU = b1500.smu3
    b1500.meas_mode(MeasMode.SAMPLING, smu)
    points = 1000
    b1500.sampling_timing(0, interval=2e-3, number=points)
    # print(b1500.read_data(1))

    spgu.output = True
    b1500.send_trigger()

    elapsed = 0
    start_time = time.perf_counter()
    while True:
        if spgu.complete:
            break
        elapsed = time.perf_counter() - start_time
    print(
        f"Elapsed: {elapsed:.1f}s / {period * repetitions:.1f}s",
    )
    import pandas

    df: pandas.DataFrame = b1500.read_data(points)
    print(df)
    df.plot(y="SMU3 Current (A)")
    # print(b1500.check_errors())
    plt.show()
    close_session()


if __name__ == "__main__":
    b1500 = connect_instrument()
    run(b1500, amplitude=3, width=1e-1, rise=5e-2, tail=5e-2, repetitions=1e1, bipolar=True)
    # run(b1500, amplitude=3, width=4e-3, rise=4e-3, tail=4e-3, repetitions=1e1, pulse_separation=False, bipolar=True)
