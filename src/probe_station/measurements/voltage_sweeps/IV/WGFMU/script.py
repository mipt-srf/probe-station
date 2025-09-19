import numpy as np
from keysight_b1530a._bindings.config import WGFMUChannel
from keysight_b1530a._bindings.configuration import set_operation_mode
from keysight_b1530a._bindings.data_retrieval import get_measurement_data, get_voltage_data
from keysight_b1530a._bindings.errors import get_error_summary
from keysight_b1530a._bindings.event_setup import set_measure_event
from keysight_b1530a._bindings.initialization import (
    clear,
    get_channel_ids,
    initialize,
    open_session,
)
from keysight_b1530a._bindings.measurement import (
    connect,
    execute,
    set_measure_current_range,
    set_measure_mode,
    wait_until_completed,
)
from keysight_b1530a._bindings.pattern_setup import (
    add_vectors,
    create_pattern,
)
from keysight_b1530a._bindings.sequence_setup import add_sequence
from keysight_b1530a._ffi import ffi, lib
from keysight_b1530a.enums import (
    WGFMUMeasureCurrentRange,
    WGFMUMeasureEvent,
    WGFMUMeasureMode,
    WGFMUOperationMode,
)
from keysight_b1530a.errors import WGFMUError
from matplotlib import pyplot as plt
from waveform_generator import PulseSequence, StaircaseSweep, TrapezoidalPulse


def get_pund_sequence(staircase_time=1e-4, steps=250, max_voltage=4, min_voltage=-4, rise_to_hold_ratio=0.01):
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

    pund = PulseSequence(positive * 2 + negative * 2 + [trapezoidal])
    pund.pulses[0].delay = time_step + edge_time
    # pund.plot()
    # (-pund).plot()
    # plt.show()
    return pund


def set_waveform(
    sequence,
    repetitions=1,
    channel=WGFMUChannel.CH1,
    measure=True,
    measure_points=1600,
    pattern_name="sequence",
):
    pattern_name += f"_{channel.name.lower()}"
    create_pattern(pattern_name, sequence.pulses[0].dc_bias)
    times, voltages = sequence.to_vectors()
    add_vectors(pattern_name, times, voltages)
    seq_time = sequence.total_duration
    if measure:
        set_measure_event(
            pattern_name=pattern_name,
            event_name="event",
            points=measure_points,
            interval=seq_time / measure_points,
            average=seq_time / measure_points,
            mode=WGFMUMeasureEvent.AVERAGED,
        )
    add_sequence(pattern_name, repetitions, channel=channel)


def run(channels=[WGFMUChannel.CH2], mode=WGFMUOperationMode.FASTIV, range=WGFMUMeasureCurrentRange.RANGE_1_UA):
    for channel in channels:
        set_operation_mode(channel, mode)
        set_measure_mode(channel, WGFMUMeasureMode.CURRENT)
        set_measure_current_range(channel, range)
        connect(channel)
    execute()
    wait_until_completed()


def get_data(repetitions, ch=WGFMUChannel.CH2, points=100):
    times, currents = get_measurement_data(ch)
    voltages = get_voltage_data(ch)

    # drop all except last rep
    times = np.split(np.array(times), repetitions)[-1]
    currents = np.split(np.array(currents), repetitions)[-1]
    voltages = np.split(np.array(voltages), repetitions)[-1]
    print(len(voltages))

    times = np.mean(times.reshape(-1, len(voltages) // points), axis=1)
    currents = np.mean(currents.reshape(-1, len(voltages) // points), axis=1)
    voltages = np.mean(voltages.reshape(-1, len(voltages) // points), axis=1)
    print(len(voltages))

    return times, voltages, currents

    # plt.plot(voltages, currents)
    # plt.figure()
    # plt.plot(times, currents)
    # plt.show()


if __name__ == "__main__":
    repetitions = 2
    clear()
    ch1 = WGFMUChannel.CH1
    ch2 = WGFMUChannel.CH2
    open_session()
    pund = get_pund_sequence()
    set_waveform(sequence=pund, repetitions=repetitions, channel=ch2)
    set_waveform(sequence=-pund, repetitions=repetitions, channel=ch1)
    try:
        run(channels=[ch1, ch2])
    except WGFMUError:
        print(get_error_summary())
        clear()
