import logging

from pymeasure.display.widgets import LogWidget
from pymeasure.experiment import BooleanParameter, FloatParameter, IntegerParameter

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.common import (
    RSU,
    BaseProcedure,
    BaseWindow,
    RSUOutputMode,
    run_app,
    setup_rsu_output,
)
from probe_station.measurements.session import Session
from probe_station.measurements.smu._widgets import IvPlotWidget
from probe_station.measurements.smu.iv_sweep_runner import run

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SmuIvSweepProcedure(BaseProcedure):
    first_voltage = FloatParameter("First voltage", units="V", default=-3)
    second_voltage = FloatParameter("Second voltage", units="V", default=3)
    top_channel = IntegerParameter("Top channel", default=4)
    bottom_channel = IntegerParameter("Bottom channel", default=3)
    average = IntegerParameter("Intergration coefficient", default=127, minimum=1, maximum=127)
    advanced_config = BooleanParameter("Advanced config", default=False)
    steps = IntegerParameter("Steps", default=100, group_by="advanced_config")
    mode = IntegerParameter("Mode", default=1, group_by="advanced_config")
    # compliance = FloatParameter("Current compliance", units="A", default=0.1, group_by="advanced_config")
    calculate_resistance = BooleanParameter("Calculate resistance", default=False)
    resistance_voltage = FloatParameter("Resistance voltage", units="V", default=1.0, group_by="calculate_resistance")

    DATA_COLUMNS = ["Voltage", "Top electrode current", "Time"]

    def startup(self):
        super().startup()
        self.b1500 = Session.acquire(timeout=60000, reset=False)
        self.b1500.clear_buffer()
        setup_rsu_output(self.b1500, rsu=RSU.RSU1, mode=RSUOutputMode.SMU)
        setup_rsu_output(self.b1500, rsu=RSU.RSU2, mode=RSUOutputMode.SMU)

    def execute(self):
        log.info(f"Starting the {self.__class__}")

        run(
            self.b1500,
            self.first_voltage,
            self.second_voltage,
            self.steps,
            top=self.top_channel,
            # current_comp=self.compliance,
            average=self.average,
            mode=self.mode,
        )

        # mode 1: one LINEAR_DOUBLE sweep → 2*steps output points
        # mode 2: two LINEAR_DOUBLE half-sweeps, each configured with steps//2 and LINEAR_DOUBLE
        if self.mode == 2:
            total_steps = 2 * self.steps - 1
        else:
            total_steps = 2 * self.steps

        for emitted, (time, current, voltage) in enumerate(self.b1500.iter_output(total_steps, 3), start=1):
            self.emit("progress", emitted / total_steps * 100)
            self.emit(
                "results",
                {"Time": time, "Voltage": voltage, "Top electrode current": current},
            )
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                self.b1500.abort()
                self.b1500.force_gnd()
                return

        self.b1500.force_gnd()


class MainWindow(BaseWindow):
    def __init__(self):
        widget_list = (
            IvPlotWidget("Results Graph", SmuIvSweepProcedure.DATA_COLUMNS),
            LogWidget("Experiment Log"),
        )
        super().__init__(
            procedure_class=SmuIvSweepProcedure,
            widget_list=widget_list,
            logger=log,
        )

        from qtpy.QtWidgets import QLabel

        self._resistance_label = QLabel()
        self.inputs.layout().addWidget(self._resistance_label)
        self.inputs.calculate_resistance.toggled.connect(self._update_resistance_visibility)
        self._update_resistance_visibility()

    def _update_resistance_visibility(self):
        enabled = self.inputs.calculate_resistance.value()
        self._resistance_label.setVisible(enabled)
        if not enabled:
            self._resistance_label.clear()

    def finished(self, experiment):
        super().finished(experiment)
        procedure = experiment.procedure
        if not getattr(procedure, "calculate_resistance", False):
            return
        self._resistance_label.setText(
            compute_branch_resistances(experiment.results.data, procedure.resistance_voltage)
        )


def compute_branch_resistances(data, target_voltage: float) -> str:
    """Compute R = V/I on the forward and backward branches of a LINEAR_DOUBLE sweep.

    Returns a human-readable summary string with both branch resistances and the
    ratio R_max / R_min. Splits the dataset in half by index: first half is the
    forward branch, second half is the backward branch.
    """
    if data.empty:
        return "Resistance: n/a (no data)"

    half = len(data) // 2
    forward = _resistance_at(data.iloc[:half], target_voltage)
    backward = _resistance_at(data.iloc[half:], target_voltage)

    lines = [
        f"Forward:  {_format_r(forward)}",
        f"Backward: {_format_r(backward)}",
    ]
    if forward and backward:
        r_fwd, r_bwd = forward[0], backward[0]
        r_max, r_min = max(r_fwd, r_bwd), min(r_fwd, r_bwd)
        if r_min != 0:
            lines.append(f"R_max / R_min: {r_max / r_min:.3f}")

    log.info("Resistance — " + " | ".join(lines))
    return "\n".join(lines)


def _resistance_at(branch, target_voltage: float):
    """Find the row closest to *target_voltage* in *branch* and return (R, V, I).

    Returns ``None`` if the branch is empty or I=0 at the closest point.
    """
    if branch.empty:
        return None
    idx = (branch["Voltage"] - target_voltage).abs().idxmin()
    v = branch["Voltage"][idx]
    i = branch["Top electrode current"][idx]
    if i == 0:
        log.warning(f"Cannot compute resistance: current is 0 at V={v:.4f} V")
        return None
    return v / i, v, i


def _format_r(result) -> str:
    if result is None:
        return "n/a"
    r, v, _ = result
    return f"{r:.3e} Ω (V={v:.3f} V)"


if __name__ == "__main__":
    setup_file_logging("logs")
    run_app(MainWindow)
