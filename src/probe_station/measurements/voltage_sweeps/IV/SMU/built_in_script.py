from pymeasure.instruments.agilent.agilentB1500 import (
    ADCMode,
    ADCType,
    MeasMode,
    MeasOpMode,
    SweepMode,
)

from probe_station.measurements.b1500 import B1500
from probe_station.measurements.common import (
    RSU,
    RSUOutputMode,
    connect_instrument,
    get_smu_by_number,
    parse_data,
    setup_rsu_output,
)


def run(b1500: B1500, start, end, steps, average=127, top=4, bottom=3, mode=1):
    # b1500.reset()
    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    smu = get_smu_by_number(b1500, top)
    smu.enable()
    smu.force("voltage", 0, 0, 1e-1)

    smu_bottom = get_smu_by_number(b1500, bottom)
    smu_bottom.enable()
    smu_bottom.force("voltage", 0, 0, 1e-1)

    # b1500.write("SSP 9,3")
    # b1500.adc_auto_zero = True
    b1500.time_stamp = True
    b1500.adc_averaging(10)
    b1500.meas_mode(MeasMode.STAIRCASE_SWEEP, smu)  # drain
    smu.meas_op_mode = MeasOpMode.CURRENT
    smu.meas_range_current = 0
    smu.adc_type = 1

    b1500.adc_setup(ADCType.HRADC, ADCMode.MANUAL, average)
    # smu.sweep_timing()

    if smu.channel in [3, 4]:
        max_voltage = max(abs(start), abs(end))
        if max_voltage <= 20:
            compliance = 100e-3
        elif 20 < max_voltage <= 40:
            compliance = 50e-3
        elif 40 < max_voltage <= 100:
            compliance = 20e-3
        else:
            raise ValueError(f"Voltages higher than 100 V are not suported by {smu.name}")
    else:
        compliance = 20e-3  # temp fix for other smus

    if mode == 1:
        smu.staircase_sweep_source(
            source_type="Voltage",
            mode=SweepMode.LINEAR_DOUBLE,
            source_range=0,
            start=start,
            stop=end,
            steps=steps,
            comp=compliance,
            # Pcomp=0.03,
        )
    elif mode == 2:
        smu.staircase_sweep_source(
            source_type="Voltage",
            mode=SweepMode.LINEAR_DOUBLE,
            source_range=0,
            start=0,
            stop=start,
            steps=steps // 2,  # fix steps num
            comp=compliance,
            # Pcomp=0.03,
        )

    b1500.clear_timer()

    b1500.send_trigger()

    if mode == 2:
        smu.staircase_sweep_source(
            source_type="Voltage",
            mode=SweepMode.LINEAR_DOUBLE,
            source_range=0,
            start=0,
            stop=end,  # fix steps
            steps=steps // 2,
            comp=compliance,
            # Pcomp=0.03,
        )

        b1500.send_trigger()

    smu.force("voltage", 0, 0)


def iter_sweep_data(b1500: B1500, total_steps: int):
    """Read IV sweep data step-by-step as each point completes (B1500 guide section 1-19).

    Uses comma as VISA termination character to read one value at a time from the
    instrument output buffer as the sweep progresses. Call after run() has sent the trigger.

    Yields (time, voltage, current) for each sweep step.
    """
    resource = b1500.adapter.connection
    resource.read_termination = ","
    total_values = total_steps * 3  # time, current, voltage per step
    try:
        buf = []
        for i in range(total_values):
            if i == total_values - 1:
                resource.read_termination = "\n"
            raw = resource.read().strip()
            buf.append(float(raw[3:]))
            if len(buf) == 3:
                time, current, voltage = buf
                buf = []
                yield time, voltage, current
    finally:
        resource.read_termination = "\n"


def get_data(b1500: B1500):
    data = parse_data(b1500.read())

    times = data[::3]
    currents = data[1::3]
    voltages = data[2::3]

    return times, voltages, currents


if __name__ == "__main__":
    b1500 = connect_instrument(reset=True)
    run(b1500, start=-3, end=3, steps=100, top=4)
    get_data(b1500)
    b1500.close_wgfmu_session()
