import numpy as np
from pymeasure.instruments.agilent.agilentB1500 import (
    ADCMode,
    ADCType,
    AgilentB1500,
    ControlMode,
    MeasMode,
    MeasOpMode,
    PgSelectorConnectionStatus,
    PgSelectorPort,
    SweepMode,
)

from probe_station.measurements.common import check_all_errors, connect_instrument, get_smu_by_number, parse_data


def run(b1500: AgilentB1500, start, end, steps, average=127, top=4, current_comp=0.001):
    b1500.control_mode = ControlMode.SMU_PGU_SELECTOR
    b1500.set_port_connection(port=PgSelectorPort.OUTPUT_2_FIRST, status=PgSelectorConnectionStatus.SMU_ON)
    b1500.set_port_connection(port=PgSelectorPort.OUTPUT_1_FIRST, status=PgSelectorConnectionStatus.SMU_ON)

    smu = get_smu_by_number(b1500, top)
    smu.enable()

    b1500.time_stamp = True
    b1500.adc_averaging(10)
    b1500.meas_mode(MeasMode.STAIRCASE_SWEEP, smu)  # drain
    smu.meas_op_mode = MeasOpMode.CURRENT
    smu.meas_range_current = 0
    smu.adc_type = 1

    b1500.adc_setup(ADCType.HRADC, ADCMode.MANUAL, average)
    # smu.sweep_timing()
    smu.staircase_sweep_source(
        source_type="Voltage",
        mode=SweepMode.LINEAR_DOUBLE,
        source_range=0,
        start=start,
        stop=end,
        steps=steps,
        comp=current_comp,
        # Pcomp=0.03,
    )

    b1500.clear_timer()

    b1500.send_trigger()

    b1500.force_gnd()


def get_data(b1500: AgilentB1500):
    data = parse_data(b1500.read())

    times = data[::3]
    currents = data[1::3]
    voltages = data[2::3]

    return times, voltages, currents


if __name__ == "__main__":
    b1500 = connect_instrument()
    run(b1500, start=-3, end=3, steps=100, top=4)
