import logging

import pyvisa
from pymeasure.instruments.keithley import Keithley2450

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def connect_instrument(address: str, timeout=60000) -> "Keithley2450Extended":
    """Connect to a Keithley 2450 instrument.

    :param address: VISA resource string (e.g. ``"TCPIP0::192.168.81.20::inst0::INSTR"``).
    :param timeout: Communication timeout in milliseconds.
    :raises ConnectionError: If the instrument cannot be reached.
    """
    try:
        smu = Keithley2450Extended(address, timeout=timeout)
        smu.clear()
        log.info("Connected to Keithley 2450 at %s", address)
        return smu
    except Exception as exc:
        raise ConnectionError(f"Could not connect to Keithley 2450 at {address}.") from exc


class Keithley2450Extended(Keithley2450):
    def __init__(self, adapter="TCPIP0::192.168.81.20::inst0::INSTR", **kwargs):
        super().__init__(adapter, write_termination="\n", name="Keithley 2450 SourceMeter", **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def wait(self):
        """Block until all pending device operations complete (*OPC? polling)."""
        self.complete
        while True:
            try:
                self.read()  # wait for the synchronization bit
                break
            except pyvisa.errors.VisaIOError:
                continue

    def get_traces(self):
        """Retrieve time, source, and reading arrays from the default trace buffer."""
        ending_index = self.trace_actual_end
        result = self.get_trace_data(ending_index)
        result = list(map(float, result.split(",")))
        return {"time": result[::3], "source": result[1::3], "reading": result[2::3]}

    def setup_sense_subsystem(self, int_time=0.1, autorange=False, compl=1e-2, range=1e-3, counts=1):
        nplc_time = int_time / (1 / 60)  # 60 Hz power supply
        self.write(":SENS:FUNC 'CURR'")
        self.autozero_once()
        self.current_autozero = "OFF"
        self.current_nplc = max(0.01, nplc_time)

        if autorange:
            self.current_autorange = True
        else:
            self.current_range = range

        self.compliance_current = compl
        if counts != 1:
            self.sense_count = counts

    def setup_source_subsystem(self, range=20, autorange=False, readback=False, delay=0):
        self.source_mode = "voltage"
        if autorange:
            self.auto_range_source()
        else:
            self.source_voltage_range = range

        if delay is not None:
            self.source_voltage_delay_auto = False
            self.source_voltage_delay = 0.001
            self.source_voltage_delay = delay
        else:
            self.source_voltage_delay_auto = True

        self.source_voltage_readback = "ON" if readback else "OFF"

    def set_terminal(self, name):
        if name == "rear":
            self.use_rear_terminals()
        elif name == "front":
            self.use_front_terminals()
        else:
            raise Exception(f"Expected 'rear' or 'front', found {name}")

    def close(self):
        self.shutdown()
