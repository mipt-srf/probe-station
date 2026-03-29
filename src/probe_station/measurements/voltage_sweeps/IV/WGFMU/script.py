import logging

import numpy as np
from keysight_b1530a._bindings.config import WGFMUChannel
from keysight_b1530a._bindings.errors import get_error_summary
from keysight_b1530a.errors import WGFMUError
from waveform_generator import PulseSequence, StaircaseSweep, TrapezoidalPulse

from probe_station.measurements.b1500 import (
    B1500,
    WGFMUMeasureCurrentRange,
    WGFMUMeasureEvent,
    WGFMUMeasureMode,
    WGFMUOperationMode,
)
from probe_station.measurements.common import connect_instrument

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def get_sequence(
    sequence_type="pund", staircase_time=1e-4, steps=250, max_voltage=4, min_voltage=-4, rise_to_hold_ratio=0.01
):
    time_step = staircase_time / steps / (1 + rise_to_hold_ratio)
    edge_time = time_step * rise_to_hold_ratio

    positive_rise = StaircaseSweep(end_voltage=max_voltage, time_step=time_step, steps=steps, edge_time=edge_time)
    positive_fall = StaircaseSweep(
        start_voltage=max_voltage, end_voltage=0, time_step=time_step, steps=steps, edge_time=edge_time
    )
    positive = [positive_rise, positive_fall]

    negative_rise = StaircaseSweep(end_voltage=min_voltage, time_step=time_step, steps=steps, edge_time=edge_time)
    negative_fall = StaircaseSweep(
        start_voltage=min_voltage, end_voltage=0, time_step=time_step, steps=steps, edge_time=edge_time
    )
    negative = [negative_rise, negative_fall]

    trapezoidal = TrapezoidalPulse(
        amplitude=0.0, pulse_width=edge_time, rise_time=10 * edge_time, fall_time=edge_time
    )  # fictional pulse to add delay at the end (otherwise last points are missed)

    if sequence_type == "pund":
        sequence = PulseSequence(positive * 2 + negative * 2 + [trapezoidal])
    else:  # default
        sequence = PulseSequence(positive + negative)

    # sequence.pulses[0].delay = time_step + edge_time
    return sequence


def set_waveform(
    b1500: B1500,
    sequence,
    repetitions=1,
    channel=WGFMUChannel.CH1,
    measure=True,
    measure_points=1600,
    pattern_name="sequence",
):
    pattern_name += f"_{channel.name.lower()}"
    b1500.create_wgfmu_pattern(pattern_name, sequence.pulses[0].dc_bias)
    times, voltages = sequence.to_vectors()
    b1500.add_vectors_to_wgfmu_pattern(pattern_name, times, voltages)
    seq_time = sequence.total_duration
    if measure:
        b1500.set_wgfmu_measure_event(
            pattern_name=pattern_name,
            event_name="event",
            points=measure_points,
            interval=seq_time / measure_points,
            average=seq_time / measure_points,
            mode=WGFMUMeasureEvent.AVERAGED,
        )
    wgfmu = b1500.wgfmus[channel - 200]
    wgfmu.add_sequence(pattern_name, repetitions=repetitions)


def run(
    b1500: B1500, channels=[WGFMUChannel.CH2], mode=WGFMUOperationMode.FASTIV, range=WGFMUMeasureCurrentRange.RANGE_1_UA
):
    for channel in channels:
        channel -= 200  # convert from 201, 202...
        wgfmu = b1500.wgfmus[channel]
        wgfmu.set_operation_mode(mode)
        wgfmu.set_measure_mode(WGFMUMeasureMode.CURRENT)
        wgfmu.set_measure_current_range(range)
        wgfmu.enable()
    b1500.run_wgfmu_measurement()


def get_data(b1500: B1500, repetitions, ch=WGFMUChannel.CH2, points=100):
    wgfmu = b1500.wgfmus[ch - 200]
    times, currents = wgfmu.get_measurement_data()
    voltages = wgfmu.get_voltage_data()

    # drop all except last rep
    times = np.split(np.array(times), repetitions)[-1]
    currents = np.split(np.array(currents), repetitions)[-1]
    voltages = np.split(np.array(voltages), repetitions)[-1]
    log.debug(f"Raw voltage array length: {len(voltages)}")

    times = np.mean(times.reshape(-1, len(voltages) // points), axis=1)
    currents = np.mean(currents.reshape(-1, len(voltages) // points), axis=1)
    voltages = np.mean(voltages.reshape(-1, len(voltages) // points), axis=1)
    log.debug(f"Decimated voltage array length: {len(voltages)}")

    return times, voltages, currents

    # plt.plot(voltages, currents)
    # plt.figure()
    # plt.plot(times, currents)
    # plt.show()


if __name__ == "__main__":
    repetitions = 2
    b1500 = connect_instrument(reset=True)
    b1500.clear()
    ch1 = WGFMUChannel.CH1
    ch2 = WGFMUChannel.CH2
    b1500.open_wgfmu_session()
    pund = get_sequence(sequence_type="pund")
    set_waveform(b1500, sequence=pund, repetitions=repetitions, channel=ch2)
    set_waveform(b1500, sequence=-pund, repetitions=repetitions, channel=ch1)
    try:
        run(b1500, channels=[ch1, ch2])
    except WGFMUError:
        print(get_error_summary())
        b1500.clear()
