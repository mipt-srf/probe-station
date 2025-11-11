import logging
import time
from time import sleep

from pymeasure.instruments.agilent.agilentB1500 import (
    SPGUChannelOutputMode,
    SPGUOperationMode,
    SPGUOutputMode,
)

from probe_station.measurements.common import (
    RSU,
    RSUOutputMode,
    check_all_errors,
    connect_instrument,
    setup_rsu_output,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

def run(b1500, repetitions, amplitude, width, rise, tail, channel=102, bipolar=False, pulse_separation=True):
    if pulse_separation:
        delay_2nd = width
    else:
        delay_2nd = tail / 4
    delay_1st = 0
    # width /= 0.85
    rise *= 0.8
    tail *= 0.8
    rise = min(rise, 1e-7)
    tail = min(tail, 1e-7)
    period = delay_1st + rise + width + tail / 0.8 + delay_2nd + width + rise + rise + tail / 0.8  # up + down
    period *= 1.025

    spgu = b1500.spgu1

    pg = None
    for ch in [spgu.ch1, spgu.ch2]:
        if ch.id == channel:
            pg = ch
            break
    if pg is None:
        raise ValueError(f"Channel {channel} not found in SPGU channels.")
    pg.enabled = True

    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SPGU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SPGU)

    spgu.operation_mode = SPGUOperationMode.PG
    if repetitions < 1e6:
        spgu.set_output_mode(mode=SPGUOutputMode.COUNT, condition=repetitions)
    else:
        spgu.set_output_mode(mode=SPGUOutputMode.DURATION, condition=period * repetitions)
    pg.load_impedance = 1e6
    spgu.period = period

    pg.set_output_voltage(source=1, peak_voltage=amplitude)

    pg.output_mode = SPGUChannelOutputMode.SIGNAL_SOURCE_1_2
    pg.set_pulse_timings(source=1, delay=delay_1st, width=width + rise, rise_time=rise, fall_time=tail)
    pg.set_pulse_timings(
        source=2, delay=delay_1st + rise + width + tail + delay_2nd, width=width + rise, rise_time=rise, fall_time=tail
    )

    # TODO: 2 pulse_width distance between pulses in both modes, fix to 1
    peak_voltage_2 = -amplitude if bipolar else amplitude
    pg.set_output_voltage(source=2, peak_voltage=peak_voltage_2)

    pg.apply_setup()
    spgu.output = True
    elapsed = 0
    start_time = time.perf_counter()
    while True:
        if spgu.complete:
            break
        elapsed = time.perf_counter() - start_time
    print(f"Elapsed: {elapsed:.1f}s / {period * repetitions:.1f}s", end="\r")

    check_all_errors(b1500)


if __name__ == "__main__":
    b1500 = connect_instrument()
    run(b1500, amplitude=3, width=1e-1, rise=100e-9, tail=100e-9, repetitions=1e1)
