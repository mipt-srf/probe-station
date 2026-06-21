"""Pymeasure base classes and application scaffolding for probe-station procedures."""

import importlib
import logging
import pkgutil
import re
import sys
import weakref
from datetime import datetime
from pathlib import Path

from pymeasure.display.widgets import LogWidget, PlotWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import Metadata, Parameter, Procedure, Results
from pymeasure.experiment.procedure import UnknownProcedure

from probe_station.logging_setup import add_file_log_dir
from probe_station.measurements import workers as _workers  # noqa: F401  -- patches pymeasure.display.manager.Worker

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Legacy data-column names -> current canonical names. Result CSVs written
# before the column-naming standardization use the old names; canonicalizing
# them on load lets plotting and analysis (which now request the new names)
# work unchanged on old and new files alike.
LEGACY_COLUMN_ALIASES = {
    "Source electrode current": "Source Current",
    "Gate current": "Gate Current",
    "Drain-Source Current": "Drain Current",
    "Top electrode current": "Top Electrode Current",
    "Top electrode Current": "Top Electrode Current",
    "Bottom electrode current": "Bottom Electrode Current",
    "Top electrode voltage": "Top Electrode Voltage",
    "Bottom electrode voltage": "Bottom Electrode Voltage",
    "Polarization current": "Polarization Current",
    "Filtered Polarization current": "Filtered Polarization Current",
    "Leakage current": "Leakage Current",
    # Keithley PUND / DC-IV: the swept source voltage and the measured current.
    "Source": "Voltage",
    "Reading": "Current",
}


def canonicalize_columns(results: Results) -> Results:
    """Rename any legacy data columns of a loaded ``Results`` to canonical names, in place.

    Reads the data once (populating the cache) and renames the cached frame, so
    every later access -- by plot curves or analysis handlers -- sees the current
    column names regardless of when the file was written.
    """
    df = results.data
    renames = {column: LEGACY_COLUMN_ALIASES[column] for column in df.columns if column in LEGACY_COLUMN_ALIASES}
    if renames:
        results._data = results._data.rename(columns=renames)
    return results

#: Default line width (in px) for all GUI plot curves.
DEFAULT_LINEWIDTH = 2


class BasePlotWidget(PlotWidget):
    """``PlotWidget`` that applies the project-wide default line width.

    Use this in place of pymeasure's ``PlotWidget`` (or subclass it, as
    :class:`~probe_station.measurements.smu._widgets.IvPlotWidget` does) so
    every GUI plot shares a single source of truth for curve thickness.
    """

    def __init__(self, *args, linewidth=DEFAULT_LINEWIDTH, **kwargs):
        super().__init__(*args, linewidth=linewidth, **kwargs)


class BaseProcedure(Procedure):
    """Base class for all probe-station procedures.

    Adds ``start_time`` and ``end_time`` metadata fields recorded into the
    CSV header. ``start_time`` lands during the standard Pymeasure flow
    (``Worker.run``: ``startup`` → ``evaluate_metadata`` → ``store_metadata``
    → ``execute``); ``end_time`` is filled here in ``shutdown()`` and
    patched into the existing header in place by
    :class:`probe_station.measurements.workers.EndTimeWorker`. Procedures
    run without that worker (e.g. the e2e test harness) still get
    ``end_time`` set on the instance — only the CSV write is skipped.
    """

    start_time = Metadata("Start time", default=0)
    end_time = Metadata("End time", default=0)

    def startup(self):
        super().startup()
        self.start_time = datetime.now()

    def shutdown(self):
        super().shutdown()
        self.end_time = datetime.now()


def take_screenshot(window, dest: str | Path, full_screen: bool = False) -> Path | None:
    """Capture a screenshot and save it to *dest*.

    :param window: The Qt widget to capture (ignored when *full_screen* is ``True``).
    :param dest: Full path (including filename) for the saved PNG.
    :param full_screen: If ``True``, capture the entire screen instead of *window*.
    :returns: Resolved path to the saved file, or ``None`` on failure.
    """
    from qtpy.QtWidgets import QApplication

    dest = Path(dest)
    try:
        if full_screen:
            pixmap = QApplication.instance().primaryScreen().grabWindow(0)
        else:
            pixmap = window.grab()
        if not pixmap.save(str(dest), "PNG"):
            logger.warning("Screenshot failed: could not save to %s", dest)
            return None
        logger.info("Screenshot saved: %s", dest)
        return dest
    except Exception as e:
        logger.warning("Screenshot failed: %s", e)
        return None


_BASE_WINDOW_INSTANCES: "weakref.WeakSet[BaseWindow]" = weakref.WeakSet()
_BUSY_PREDICATES: list = []


def register_busy_predicate(fn) -> None:
    """Register a callable returning a busy description, or ``None`` if idle.

    Used by :meth:`BaseWindow._queue` to gate queueing against non-window
    instrument users (e.g. the launcher's reset action). Predicates are
    polled on every queue click; keep them cheap.
    """
    _BUSY_PREDICATES.append(fn)


def any_window_running() -> str | None:
    """Return the title of any in-process window currently measuring, else None."""
    for w in _BASE_WINDOW_INSTANCES:
        if w.manager.is_running():
            return w.windowTitle()
    return None


class BaseWindow(ManagedWindowBase):
    """Base class for all probe-station measurement windows.

    ``inputs`` and ``displays`` default to all parameters declared on
    ``procedure_class`` (in definition order).  Pass explicit lists to override.

    ``widget_list`` defaults to ``(BasePlotWidget("Results Graph", DATA_COLUMNS),
    LogWidget("Experiment Log"))`` when the procedure defines non-empty
    ``DATA_COLUMNS``, otherwise ``(LogWidget("Experiment Log"),)``.

    An optional ``logger`` is connected to the window's log level and the
    ``LogWidget`` found in ``widget_list`` (looked up by type, not by index).

    ``store_measurement`` defaults to ``False`` (the "Save data" checkbox starts
    unchecked).  Set ``self.store_measurement = True`` in a subclass ``__init__``
    after calling ``super().__init__()`` to start with data storage enabled.

    When data storage is enabled (``store_measurement`` is ``True``), logs are
    written to a ``logs/`` subdirectory of the results directory and a screenshot
    is saved next to the results file when the measurement finishes.
    """

    def __init__(self, *args, procedure_class, widget_list=None, inputs=None, displays=None, logger=None, **kwargs):
        if widget_list is None:
            columns = getattr(procedure_class, "DATA_COLUMNS", [])
            if columns:
                widget_list = (
                    BasePlotWidget("Results Graph", columns),
                    LogWidget("Experiment Log"),
                )
            else:
                widget_list = (LogWidget("Experiment Log"),)

        if inputs is None:
            # Collect all Parameter fields in definition order across the MRO.
            seen: set[str] = set()
            inputs = []
            for cls in reversed(procedure_class.__mro__):
                for name, obj in cls.__dict__.items():
                    if isinstance(obj, Parameter) and name not in seen:
                        seen.add(name)
                        inputs.append(name)

        if displays is None:
            displays = inputs

        super().__init__(
            *args, procedure_class=procedure_class, widget_list=widget_list, inputs=inputs, displays=displays, **kwargs
        )

        log_widget = next((w for w in widget_list if isinstance(w, LogWidget)), None)
        if log_widget is not None:
            log_widget.handler.setLevel(logging.INFO)
            logging.getLogger().addHandler(log_widget.handler)
        if logger is not None:
            logger.setLevel(self.log_level)
            logger.info("ManagedWindow connected to logging")

        self.setWindowTitle(self.procedure_class.__name__)
        self.store_measurement = False
        self.filename = f"{{date}}_{{time}}_{self.procedure_class.__name__}"
        _BASE_WINDOW_INSTANCES.add(self)

    def _queue(self, checked):
        # Serialize measurements across all open windows in the same process:
        # the B1500 is a single shared resource (see Session singleton), and
        # two concurrent Workers would corrupt each other's VISA traffic.
        busy = [w.windowTitle() for w in _BASE_WINDOW_INSTANCES if w is not self and w.manager.is_running()]
        for fn in _BUSY_PREDICATES:
            desc = fn()
            if desc:
                busy.append(desc)
        if busy:
            msg = f"Cannot queue: another measurement is running ({', '.join(busy)})"
            logger.warning(msg)
            self.statusBar().showMessage(msg, 5000)
            return
        if self.store_measurement:
            add_file_log_dir(Path(self.directory) / "logs")
        super()._queue(checked)

    def finished(self, experiment):
        super().finished(experiment)
        if not self.store_measurement:
            return
        # Save the screenshot next to the results file, sharing its name.
        dest = Path(experiment.results.data_filename).with_suffix(".png")
        take_screenshot(self, dest)

    def load_experiment_from_file(self, filename: str) -> None:
        """Load a saved Pymeasure CSV into this window as a new curve.

        Mirrors the inner load loop of
        :meth:`pymeasure.display.windows.managed_window.ManagedWindowBase.open_experiment`
        so a file picked outside the window's own Open dialog (e.g. via the
        launcher's data reader) is added with the same curve and per-experiment
        metadata browser entry as the toolbar Open action.
        """
        if filename in self.manager.experiments:
            return
        results = load_results(filename)
        experiment = self.new_experiment(results)
        for curve in experiment.curve_list:
            if curve:
                curve.update_data()
        experiment.browser_item.progressbar.setValue(100)
        self.manager.load(experiment)


def _read_procedure_class_name(path: str | Path) -> str | None:
    """Return the bare procedure class name from a results-file header, or ``None``."""
    with open(path, encoding=Results.ENCODING) as f:
        for line in f:
            if not line.startswith(Results.COMMENT):
                break
            stripped = line[1:].strip()
            if stripped.startswith("Procedure:"):
                match = re.search(r"<(?:.*\.)?(?P<class>[^.>]+)>", stripped)
                if match:
                    return match.group("class")
    return None


def _find_procedure_class(class_name: str) -> type[Procedure] | None:
    """Locate a :class:`Procedure` subclass by name within ``probe_station.measurements``.

    Used to reconstruct procedures recorded as living in ``__main__`` -- i.e. run
    as a standalone script rather than launched in-process. Imports each
    submodule (skipping any that fail, e.g. a missing instrument backend) and
    returns the class from the module that actually defines it.
    """
    import probe_station.measurements as pkg

    for info in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        try:
            module = importlib.import_module(info.name)
        except Exception:
            continue
        candidate = getattr(module, class_name, None)
        if isinstance(candidate, type) and issubclass(candidate, Procedure) and candidate.__module__ == info.name:
            return candidate
    return None


def load_results(path: str | Path) -> Results:
    """Load a Pymeasure ``Results``, tolerating procedures run outside the launcher.

    A procedure run as a standalone script records its class as living in
    ``__main__``, so Pymeasure cannot reconstruct it from the header (it raises
    ``AttributeError`` or ``ImportError``). In that case we locate the class by
    name within ``probe_station.measurements`` and reload with it imported from
    its real module.
    """
    try:
        results = Results.load(str(path))
    except (AttributeError, ImportError):
        class_name = _read_procedure_class_name(path)
        procedure_cls = _find_procedure_class(class_name) if class_name else None
        if procedure_cls is None:
            raise
        results = Results.load(str(path), procedure_class=procedure_cls)
    return canonicalize_columns(results)


def read_procedure_class(path: str | Path) -> tuple[type[Procedure], type[BaseWindow]]:
    """Resolve the procedure and window class for a Pymeasure results CSV.

    Parses the file header via :func:`load_results` — which imports the
    procedure module and rebuilds the procedure instance — then looks up the
    ``MainWindow`` defined in the same module by convention.

    Raises :class:`ValueError` with a user-readable message if the header
    is missing the ``Procedure`` line, the module cannot be imported, or
    no ``MainWindow`` is defined alongside the procedure.
    """
    try:
        results = load_results(path)
    except Exception as e:
        raise ValueError(f"Could not read Pymeasure header from {path}: {e}") from e
    procedure_class = type(results.procedure)
    if procedure_class is UnknownProcedure:
        raise ValueError(
            f"The Procedure class referenced in {path} could not be imported. " "It may have been renamed or removed."
        )
    module = sys.modules.get(procedure_class.__module__)
    window_class = getattr(module, "MainWindow", None) if module is not None else None
    if window_class is None:
        raise ValueError(f"No MainWindow defined in {procedure_class.__module__} " f"for {procedure_class.__name__}")
    return procedure_class, window_class


def run_app(window_class):
    """Launch a pymeasure ManagedWindow application.

    Sets the locale to English (to prevent decimal-comma issues), creates the
    Qt application, shows the window, and starts the event loop.  Intended for
    use in ``if __name__ == "__main__"`` blocks.

    :param window_class: A ``ManagedWindowBase`` subclass to instantiate and show.
    """
    import sys

    from pymeasure.display.Qt import QtWidgets
    from qtpy.QtCore import QLocale

    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QtWidgets.QApplication(sys.argv)
    window = window_class()
    window.show()
    app.exec()
