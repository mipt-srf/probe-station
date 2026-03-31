import logging
import time

from pymeasure.instruments.agilent.agilentB1500 import (
    SMU,
    SPGU,
    ALWGPattern,
    MeasMode,
    MeasOpMode,
    SPGUChannel,
    SPGUOperationMode,
    SPGUOutputMode,
)

from probe_station.measurements.b1500 import B1500
from probe_station.measurements.common import (
    RSU,
    RSUOutputMode,
    connect_instrument,
    get_smu_by_number,
    setup_rsu_output,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def run(b1500: B1500, repetitions, amplitude, rise, tail, channel=102, smu_ch=1, bipolar=False):
    # Total duration of one two-pulse sequence (used for DURATION output mode)
    period = 2 * (rise + tail)

    spgu: SPGU = b1500.spgu1

    pg = None
    for ch in [spgu.ch1, spgu.ch2]:
        if ch.id == channel:
            pg: SPGUChannel = ch
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

    smu: SMU = get_smu_by_number(b1500, smu_ch)
    smu_voltage: SMU = get_smu_by_number(b1500, 4)

    b1500.time_stamp = True
    b1500.meas_mode(MeasMode.SAMPLING, smu)

    # smu.meas_op_mode = MeasOpMode.CURRENT
    smu_voltage.meas_op_mode = MeasOpMode.VOLTAGE

    # points = 1000
    interval = 2e-3
    points = int(period * repetitions / interval)
    b1500.sampling_timing(0, interval=interval, number=points)
    # print(b1500.read_data(1))

    b1500.write("MCC")
    b1500.check_errors()
    # spgu.output = True
    b1500.write(f"MSP {pg.id}")
    b1500.clear_timer()
    b1500.send_trigger()

    elapsed = 0
    start_time = time.perf_counter()
    while True:
        if spgu.complete:
            break
        elapsed = time.perf_counter() - start_time
    log.info(f"Elapsed: {elapsed:.1f}s / {period * repetitions:.1f}s")

    # df: pandas.DataFrame = b1500.read_data(points)
    # if log.isEnabledFor(logging.DEBUG):
    # log.debug(f"Measurement data (shape={df.shape}):\n{df.head()}")
    # print(df)
    # df.plot(y=f"SMU{4} Voltage (V)")
    # df.plot(
    # x=f"SMU{smu_ch} Time (s)", y=f"SMU{smu_ch} Current (A)"
    # )  # TODO: сейчас SMU начинает измерять позже SPGU output -> не виден ток в начале. Нужно либо убрать триггер, и запускать измерения вручную (мб получиться обойти 2e-3 ограничение), либо захардкодить output нуля в начале ALWG
    # print(b1500.check_errors())
    # plt.show()
    # close_session()


if __name__ == "__main__":
    b1500 = connect_instrument()
    run(b1500, amplitude=3, rise=5e-2, tail=5e-2, repetitions=1, bipolar=True)
    # run(b1500, amplitude=3, width=4e-3, rise=4e-3, tail=4e-3, repetitions=1e1, pulse_separation=False, bipolar=True)
