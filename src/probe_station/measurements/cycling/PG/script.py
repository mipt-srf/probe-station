from pymeasure.instruments.agilent import AgilentB1500
from pymeasure.instruments.agilent.agilentB1500 import (
    ControlMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
    SPGUChannelOutputMode,
    SPGUOperationMode,
    SPGUOutputMode,
)


def connect_instrument():
    """Connect to the Agilent B1500 instrument."""
    try:
        b1500 = AgilentB1500("USB1::0x0957::0x0001::0001::0::INSTR", timeout=60000)
        b1500.reset()
        b1500.initialize_all_smus()
        b1500.initialize_all_spgus()
        b1500.data_format(1, mode=1)  # 21 for new, 1 for old (?)

        return b1500
    except Exception as e:
        print(f"Error connecting to instrument: {e}")
        return None


def run(b1500, repetitions, amplitude, width, rise, tail, channel=102, bipolar=False):
    delay_1st = 0
    delay_2nd = 2 * width
    period = (delay_2nd + (rise + width + tail) * 2) + delay_2nd  # up + down
    # width /= 0.85
    rise *= 0.8
    tail *= 0.8

    spgu = b1500.spgu1

    pg = None
    for ch in [spgu.ch1, spgu.ch2]:
        if ch.channel == channel:
            pg = ch
            break
    if pg is None:
        raise ValueError(f"Channel {channel} not found in SPGU channels.")
    pg.enable()

    b1500.control_mode = ControlMode.SMU_PGU_SELECTOR
    if pg.channel == 102:
        b1500.set_port_connection(port=PgSelectorPort.OUTPUT_2_FIRST, status=PgSelectorConnectionStatus.PGU_ON)
    elif pg.channel == 101:
        b1500.set_port_connection(port=PgSelectorPort.OUTPUT_1_FIRST, status=PgSelectorConnectionStatus.PGU_ON)

    spgu.operation_mode = SPGUOperationMode.PG
    spgu.set_output_mode(mode=SPGUOutputMode.COUNT, condition=repetitions)
    # print(b1500._spgu_names, b1500._spgu_references)
    # print(b1500.get_spgu_output())
    # b1500.write(f"ODSW {ch2},0")
    pg.load_impedance = 1e6
    spgu.period = period

    pg.set_output_voltage(source=1, peak_voltage=amplitude)

    pg.output_mode = SPGUChannelOutputMode.SIGNAL_SOURCE_1_2
    pg.set_pulse_timings(source=1, delay=delay_1st, width=width + rise, rise_time=rise)
    pg.set_pulse_timings(
        source=2,
        delay=delay_1st + width + rise + tail + delay_2nd,
        width=width + rise,
        rise_time=rise,
    )

    # TODO: 2 pulse_width distance between pulses in both modes, fix to 1
    peak_voltage_2 = -amplitude if bipolar else amplitude
    pg.set_output_voltage(source=2, peak_voltage=peak_voltage_2)

    # pg2.load_impedance = 1
    pg.apply_setup()
    spgu.start_output()
    print("finished")

    while True:
        try:
            b1500.check_errors()
        except Exception as e:
            print(e)
        else:
            break


if __name__ == "__main__":
    b1500 = connect_instrument()
    run(b1500, amplitude=3, width=1e-1, rise=100e-9, tail=100e-9, repetitions=1e1)
