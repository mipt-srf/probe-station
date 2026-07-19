from probe_station.measurements.b1500 import (
    B1500,
    ADCMode,
    ADCType,
    MeasMode,
    MeasOpMode,
    SweepMode,
)
from probe_station.measurements.b1500_helpers import connect_instrument, max_compliance, parse_data
from probe_station.measurements.rsu import RSU, RSUOutputMode, setup_rsu_output


def run(b1500: B1500, start, end, steps, average=127, top=4, bottom=3, mode=1, gate=1, gate_voltage=1, base=2):
    # b1500.reset()
    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    smu = b1500.smus[top]
    smu.enable()

    smu_bottom = b1500.smus[bottom]
    smu_bottom.enable()

    gate_smu = b1500.smus[gate]
    gate_smu.enable()

    base_smu = b1500.smus[base]
    base_smu.enable()

    peak = max(abs(start), abs(end))
    smu.force("voltage", 0, 0, max_compliance(smu, peak))
    smu_bottom.force("voltage", 0, 0, max_compliance(smu_bottom, 0))
    gate_smu.force("voltage", 0, gate_voltage, max_compliance(gate_smu, abs(gate_voltage)))
    base_smu.force("voltage", 0, 0, max_compliance(base_smu, 0))

    # b1500.write("SSP 9,3")
    # b1500.adc_auto_zero = True
    b1500.time_stamp = True
    b1500.adc_averaging(10)
    b1500.meas_mode(MeasMode.STAIRCASE_SWEEP, smu, gate_smu)  # drain + gate
    smu.meas_op_mode = MeasOpMode.CURRENT
    gate_smu.meas_op_mode = MeasOpMode.CURRENT
    smu.meas_range_current = 0
    gate_smu.meas_range_current = 0
    smu.adc_type = 1
    gate_smu.adc_type = 1

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


def get_data(b1500: B1500):
    data = parse_data(b1500.read())

    times = data[::5]
    currents = data[1::5]
    gate_currents = data[3::5]
    voltages = data[4::5]

    return times, voltages, currents, gate_currents


if __name__ == "__main__":
    b1500 = connect_instrument(reset=True)
    run(b1500, start=-3, end=3, steps=100, top=4, gate=1)
    get_data(b1500)
    b1500.close_wgfmu_session()
