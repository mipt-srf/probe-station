from keysight_b1530a._bindings.initialization import close_session, open_session
from pymeasure.instruments.agilent.agilentB1500 import (
    ADCMode,
    ADCType,
    AgilentB1500,
    MeasMode,
    MeasOpMode,
    SweepMode,
)

from probe_station.measurements.common import (
    RSU,
    RSUOutputMode,
    connect_instrument,
    get_smu_by_number,
    parse_data,
    setup_rsu_output,
)


def run(b1500: AgilentB1500, start, end, steps, average=127, top=4, bottom=3):
    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    smu = get_smu_by_number(b1500, top)
    smu.enable()
    smu.force("voltage", 0, 0)

    smu_bottom = get_smu_by_number(b1500, bottom)
    smu_bottom.enable()
    smu_bottom.force("voltage", 0, 0)

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

    b1500.clear_timer()

    b1500.send_trigger()

    smu.force("voltage", 0, 0)


def get_data(b1500: AgilentB1500):
    data = parse_data(b1500.read())

    times = data[::3]
    currents = data[1::3]
    voltages = data[2::3]

    return times, voltages, currents


if __name__ == "__main__":
    b1500 = connect_instrument(reset=True)
    open_session()
    run(b1500, start=-3, end=3, steps=100, top=4)
    get_data(b1500)
    close_session()
