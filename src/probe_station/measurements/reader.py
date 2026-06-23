"""Cross-procedure data reader shared by the launcher's "Open data" button and the ``reader`` command.

The reader browses Pymeasure result CSVs across every procedure, sniffs the
producing procedure from each file header, and opens it in the matching
measurement window. It is used both as an in-launcher dialog (see
:func:`open_data`) and as a standalone application (see :func:`main`).
"""

import logging
import os
import sys

from pymeasure.display.widgets import ResultsDialog
from qtpy.QtCore import QLocale, Qt
from qtpy.QtWidgets import (
    QApplication,
    QMessageBox,
    QTabWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.pymeasure_base import (
    BasePlotWidget,
    load_results,
    read_procedure_class,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class CrossProcedureResultsDialog(ResultsDialog):
    """``ResultsDialog`` that infers the procedure class from each clicked file
    and swaps a matching plot-preview tab on the fly.

    Pymeasure's stock dialog expects a single ``procedure_class`` + ``widget_list``
    fixed at construction time. The reader browses files across procedures, so we
    override ``update_preview`` to (1) sniff the producing procedure from the file
    header, (2) build (and cache) a ``BasePlotWidget`` preview keyed off that
    procedure's ``DATA_COLUMNS``, and (3) repopulate parameters/metadata from the
    reconstructed procedure.
    """

    def __init__(self, parent=None):
        super().__init__(procedure_class=None, widget_list=(), parent=parent)
        # The preview tab built by ``_setup_ui`` is the only QTabWidget child.
        self._preview_tab: QTabWidget = self.findChild(QTabWidget)
        self._plot_container = QWidget()
        self._plot_layout = QVBoxLayout()
        self._plot_layout.setContentsMargins(0, 0, 0, 0)
        self._plot_container.setLayout(self._plot_layout)
        self._preview_tab.insertTab(0, self._plot_container, "Results Graph")
        self._preview_tab.setCurrentIndex(0)
        self._plot_cache: dict[type, BasePlotWidget | None] = {}
        self._current_plot: BasePlotWidget | None = None
        # Causes large delays when nas is not accessible. Maybe it's worth to consider to add this functionality only when .[measurements] is installed or to add a config option to enable/disable it.
        # sidebar = self.sidebarUrls()
        # nas_url = QUrl.fromLocalFile(NAS_DATA_ROOT)
        # if nas_url not in sidebar:
        #     sidebar.append(nas_url)
        #     self.setSidebarUrls(sidebar)

    def _ensure_plot_preview(self, procedure_class: type) -> None:
        if procedure_class in self._plot_cache:
            new_widget = self._plot_cache[procedure_class]
        else:
            columns = getattr(procedure_class, "DATA_COLUMNS", None)
            new_widget = BasePlotWidget("Plot preview", columns) if columns else None
            self._plot_cache[procedure_class] = new_widget
        if new_widget is self._current_plot:
            return
        if self._current_plot is not None:
            self._plot_layout.removeWidget(self._current_plot)
            self._current_plot.setParent(None)
        if new_widget is not None:
            self._plot_layout.addWidget(new_widget)
        self._current_plot = new_widget

    def update_preview(self, filename: str) -> None:
        if os.path.isdir(filename) or filename == "":
            return
        try:
            results = load_results(filename)
        except (ValueError, AttributeError, ImportError):
            return

        self._ensure_plot_preview(type(results.procedure))
        if self._current_plot is not None:
            self._current_plot.clear_widget()
            self._current_plot.load(self._current_plot.new_curve(results))

        self.preview_param.clear()
        for _, param in results.procedure.parameter_objects().items():
            self.preview_param.addTopLevelItem(QTreeWidgetItem([param.name, str(param)]))
        self.preview_param.sortItems(0, Qt.AscendingOrder)

        self.preview_metadata.clear()
        for _, metadata in results.procedure.metadata_objects().items():
            self.preview_metadata.addTopLevelItem(QTreeWidgetItem([metadata.name, str(metadata)]))
        self.preview_metadata.sortItems(0, Qt.AscendingOrder)


def open_data(parent: QWidget | None, child_windows: list) -> None:
    """Show the cross-procedure Open dialog and load the chosen files.

    Picked files are grouped by their window class so multiple files from the
    same procedure stack as curves in a single window, matching Pymeasure's
    native Open behavior. Each constructed window is appended to *child_windows*
    so the caller keeps a strong reference (otherwise the windows are GC'd).

    :param parent: Parent for the warning dialogs. The Open dialog itself is
        created without a parent so a launcher's dark stylesheet does not
        cascade into it.
    :param child_windows: List the opened measurement windows are appended to.
    """
    dialog = CrossProcedureResultsDialog()
    dialog.setWindowTitle("Open results file")
    if not dialog.exec():
        return
    filenames = dialog.selectedFiles()
    if not filenames:
        return
    windows: dict[type, QWidget] = {}
    for filename in filenames:
        try:
            _, window_class = read_procedure_class(filename)
        except ValueError as e:
            QMessageBox.warning(parent, "Cannot open file", str(e))
            continue
        window = windows.get(window_class)
        if window is None:
            try:
                window = window_class()
            except Exception:
                logger.exception("Failed to construct %s for %s", window_class.__name__, filename)
                QMessageBox.warning(
                    parent,
                    "Cannot open file",
                    f"Failed to construct {window_class.__name__}. See logs for details.",
                )
                continue
            child_windows.append(window)
            window.show()
            windows[window_class] = window
        try:
            window.load_experiment_from_file(filename)
        except Exception:
            logger.exception("Failed to load %s into %s", filename, window_class.__name__)
            QMessageBox.warning(
                parent,
                "Cannot open file",
                f"Failed to load data from {filename}. See logs for details.",
            )


def main():
    setup_file_logging("logs")
    # Match the locale that run_app() sets for standalone procedure runs so
    # opened windows see dot-decimal input parsing too.
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QApplication(sys.argv)

    # Strong refs to the windows opened from the picked files; keeps them alive
    # for the duration of the event loop.
    child_windows: list = []
    open_data(parent=None, child_windows=child_windows)
    if not child_windows:
        # User cancelled the dialog or picked nothing -- nothing to keep open.
        return
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
