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


def run(
    b1500: B1500,
    start,
    end,
    steps,
    average=127,
    drain=1,
    source=3,
    mode=1,
    gate=4,
    drain_voltage=1,
    base=2,
):
    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    gate_smu = b1500.smus[gate]  # swept channel
    gate_smu.enable()

    drain_smu = b1500.smus[drain]
    drain_smu.enable()

    source_smu = b1500.smus[source]
    source_smu.enable()

    base_smu = b1500.smus[base]
    base_smu.enable()

    peak = max(abs(start), abs(end))
    gate_smu.force("voltage", 0, 0, max_compliance(gate_smu, peak))
    source_smu.force("voltage", 0, 0, max_compliance(source_smu, 0))
    drain_smu.force("voltage", 0, drain_voltage, max_compliance(drain_smu, abs(drain_voltage)))
    base_smu.force("voltage", 0, 0, max_compliance(base_smu, 0))

    b1500.time_stamp = True
    b1500.adc_averaging(10)
    # Measure drain then gate; the swept source (gate) voltage is appended last.
    b1500.meas_mode(MeasMode.STAIRCASE_SWEEP, drain_smu, gate_smu)
    drain_smu.meas_op_mode = MeasOpMode.CURRENT
    gate_smu.meas_op_mode = MeasOpMode.CURRENT
    drain_smu.meas_range_current = 0
    gate_smu.meas_range_current = 0
    drain_smu.adc_type = 1
    gate_smu.adc_type = 1

    b1500.adc_setup(ADCType.HRADC, ADCMode.MANUAL, average)

    compliance = max_compliance(gate_smu, peak)

    if mode == 1:
        gate_smu.staircase_sweep_source(
            source_type="Voltage",
            mode=SweepMode.LINEAR_DOUBLE,
            source_range=0,
            start=start,
            stop=end,
            steps=steps,
            comp=compliance,
        )
    elif mode == 2:
        gate_smu.staircase_sweep_source(
            source_type="Voltage",
            mode=SweepMode.LINEAR_DOUBLE,
            source_range=0,
            start=0,
            stop=start,
            steps=steps // 2,  # fix steps num
            comp=compliance,
        )

    b1500.clear_timer()

    b1500.send_trigger()

    if mode == 2:
        gate_smu.staircase_sweep_source(
            source_type="Voltage",
            mode=SweepMode.LINEAR_DOUBLE,
            source_range=0,
            start=0,
            stop=end,  # fix steps
            steps=steps // 2,
            comp=compliance,
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
    run(b1500, start=-20, end=20, steps=100, drain=1, gate=4)
    get_data(b1500)
    b1500.close_wgfmu_session()
