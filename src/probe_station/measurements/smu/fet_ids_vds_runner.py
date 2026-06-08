from pymeasure.instruments.agilent.agilentB1500 import (
    ADCMode,
    ADCType,
    MeasMode,
    MeasOpMode,
    SweepMode,
)

from probe_station.measurements.b1500 import B1500
from probe_station.measurements.b1500_helpers import channel_letter, connect_instrument, max_compliance
from probe_station.measurements.rsu import RSU, RSUOutputMode, setup_rsu_output


def run(b1500: B1500, start, end, steps, average=127, top=4, bottom=3, mode=1, gate=1, gate_voltage=1):
    # b1500.reset()
    setup_rsu_output(b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
    setup_rsu_output(b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    smu = b1500.smus[top]
    smu.enable()

    smu_bottom = b1500.smus[bottom]
    smu_bottom.enable()

    gate_smu = b1500.smus[gate]
    gate_smu.enable()

    peak = max(abs(start), abs(end))
    smu.force("voltage", 0, 0, max_compliance(smu, peak))
    smu_bottom.force("voltage", 0, 0, max_compliance(smu_bottom, 0))
    gate_smu.force("voltage", 0, gate_voltage, max_compliance(gate_smu, abs(gate_voltage)))

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


def get_data(b1500: B1500, top=4, gate=1):
    """Parse one batch readout into ``(times, voltages, currents, gate_currents)``.

    Routes each value by its ``FMT1`` channel/type prefix (``T`` time, ``I`` current,
    ``V`` source voltage) rather than by a fixed token order, so drain and gate columns
    cannot silently transpose if the instrument interleaves the channels differently.

    :param top: Channel number of the swept source / drain-current electrode.
    :param gate: Channel number of the gate.
    """
    top_letter = channel_letter(top)
    gate_letter = channel_letter(gate)

    times: list[float] = []
    voltages: list[float] = []
    currents: list[float] = []
    gate_currents: list[float] = []
    for token in b1500.read().split(","):
        if len(token) < 4:
            continue
        channel = token[1]
        data_type = token[2]
        value = float(token[3:])
        if data_type == "T" and channel == top_letter:
            times.append(value)
        elif data_type == "I" and channel == top_letter:
            currents.append(value)
        elif data_type == "I" and channel == gate_letter:
            gate_currents.append(value)
        elif data_type == "V":
            voltages.append(value)

    return times, voltages, currents, gate_currents


if __name__ == "__main__":
    b1500 = connect_instrument(reset=True)
    run(b1500, start=-3, end=3, steps=100, top=4, gate=1)
    get_data(b1500, top=4, gate=1)
    b1500.close_wgfmu_session()
