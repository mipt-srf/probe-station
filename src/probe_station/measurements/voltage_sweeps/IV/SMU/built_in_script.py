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
    max_compliance,
    parse_data,
    setup_rsu_output,
)


def run(b1500: B1500, start, end, steps, average=127, top=4, bottom=3, mode=1):
    # b1500.reset()
    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    smu = get_smu_by_number(b1500, top)
    smu.enable()

    smu_bottom = get_smu_by_number(b1500, bottom)
    smu_bottom.enable()

    peak = max(abs(start), abs(end))
    smu.force("voltage", 0, 0, max_compliance(smu, peak))
    smu_bottom.force("voltage", 0, 0, max_compliance(smu_bottom, 0))

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

    compliance = max_compliance(smu, peak)

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
