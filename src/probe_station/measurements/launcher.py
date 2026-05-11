import importlib
import logging
import os
import subprocess
import sys

from pymeasure.display.widgets import PlotWidget, ResultsDialog
from pymeasure.experiment import Results
from qtpy.QtCore import QLocale, Qt, QThread
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.common import (
    any_window_running,
    read_procedure_class,
    register_busy_predicate,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# Name of the in-flight action (e.g. "Вжух"), or None if idle. Read by the
# busy predicate so procedure windows refuse to queue while it's running.
_running_action: str | None = None


def _action_busy() -> str | None:
    return _running_action


register_busy_predicate(_action_busy)


class ScriptRunner(QThread):
    def __init__(self, script_module, kind="subprocess"):
        super().__init__()
        self.script_module = script_module
        self.kind = kind

    def run(self):
        try:
            if self.kind == "notebook":
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "jupyter",
                        "nbconvert",
                        "--execute",
                        "--to",
                        "notebook",
                        "--inplace",
                        self.script_module,
                    ]
                )
            else:
                subprocess.Popen([sys.executable, "-m", self.script_module])
        except Exception as e:
            log.exception(f"Error running {self.script_module}: {e}")


class ActionRunner(QThread):
    """Runs ``module.run()`` off the GUI thread for ``kind='action'`` buttons."""

    def __init__(self, script_module, label):
        super().__init__()
        self.script_module = script_module
        self.label = label

    def run(self):
        try:
            module = importlib.import_module(self.script_module)
            module.run()
        except Exception:
            log.exception("Error running action %s", self.script_module)


class ModernButton(QPushButton):
    def __init__(self, text, color="#4CAF50"):
        super().__init__(text)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                color: white;
                padding: 15px 32px;
                text-align: center;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                margin: 5px;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color, 0.8)};
            }}
        """)

    def _darken_color(self, hex_color, factor=0.9):
        # Simple color darkening
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        darkened = tuple(int(c * factor) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"


class CrossProcedureResultsDialog(ResultsDialog):
    """``ResultsDialog`` that infers the procedure class from each clicked file
    and swaps a matching plot-preview tab on the fly.

    Pymeasure's stock dialog expects a single ``procedure_class`` + ``widget_list``
    fixed at construction time. The launcher's data reader browses files across
    procedures, so we override ``update_preview`` to (1) sniff the producing
    procedure from the file header, (2) build (and cache) a ``PlotWidget``
    preview keyed off that procedure's ``DATA_COLUMNS``, and (3) repopulate
    parameters/metadata from the reconstructed procedure.
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
        self._plot_cache: dict[type, PlotWidget | None] = {}
        self._current_plot: PlotWidget | None = None

    def _ensure_plot_preview(self, procedure_class: type) -> None:
        if procedure_class in self._plot_cache:
            new_widget = self._plot_cache[procedure_class]
        else:
            columns = getattr(procedure_class, "DATA_COLUMNS", None)
            new_widget = PlotWidget("Plot preview", columns) if columns else None
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
            results = Results.load(str(filename))
        except ValueError:
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


class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Measurement Scripts")
        self.setGeometry(300, 300, 450, 600)
        self.threads = []
        # Hold strong refs to in-process child windows so they aren't GC'd.
        self.child_windows = []

        # Modern dark theme
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
        """)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title = QLabel("Measurement Scripts Launcher")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #4CAF50; margin-bottom: 20px;")
        layout.addWidget(title)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #555555; height: 2px;")
        layout.addWidget(separator)

        # Script buttons.  4th element is the launch ``kind``:
        # "subprocess" (default) | "in_process" | "notebook".
        scripts = [
            ("🔄 Cycling Procedure (SPGU)", "probe_station.measurements.cycling.PG.procedure", "#4CAF50", "in_process"),
            (
                "🔄 IV Procedure (SPGU) - experimental",
                "probe_station.measurements.voltage_sweeps.IV.pg_with_current_measurement_procedure",
                "#4CAF50",
                "in_process",
            ),
            (
                "🔄 Cycling Procedure (WGFMU)",
                "probe_station.measurements.cycling.WGFMU.procedure",
                "#2196F3",
                "in_process",
            ),
            (
                "📊 Fast IV Procedure (WGFMU)",
                "probe_station.measurements.voltage_sweeps.IV.WGFMU.procedure",
                "#2196F3",
                "in_process",
            ),
            (
                "📊 CV Sweep Procedure (CMU)",
                "probe_station.measurements.voltage_sweeps.CV.procedure",
                "#C224BA",
                "in_process",
            ),
            (
                "📊 IV Sweep Procedure (SMU)",
                "probe_station.measurements.voltage_sweeps.IV.SMU.built_in_procedure",
                "#D1B122",
                "in_process",
            ),
            (
                "📊 Ids (Vg)",
                "probe_station.measurements.voltage_sweeps.IV.SMU.procedure_Ids_Vg",
                "#D1B122",
                "in_process",
            ),
            (
                "📊 Ids (Vds)",
                "probe_station.measurements.voltage_sweeps.IV.SMU.procedure_Ids_Vds",
                "#D1B122",
                "in_process",
            ),
            ("✨ Вжух", "probe_station.measurements.magic", "#D1B122", "action"),
            # ("📈 Staircase Sweep", "test_staircase_sweep_source.ipynb", "#FF9800", "notebook"),
        ]

        for script_data in scripts:
            if len(script_data) == 4:
                name, module, color, kind = script_data
            else:
                name, module, color = script_data
                kind = "subprocess"

            button = ModernButton(name, color)
            button.clicked.connect(lambda checked, m=module, k=kind: self.run_script(m, k))
            layout.addWidget(button)

        layout.addStretch()

        reader_separator = QFrame()
        reader_separator.setFrameShape(QFrame.HLine)
        reader_separator.setStyleSheet("background-color: #555555; height: 2px;")
        layout.addWidget(reader_separator)

        open_data_button = ModernButton("📁 Open data…", "#9C27B0")
        open_data_button.clicked.connect(self.open_data)
        layout.addWidget(open_data_button)

        # Footer
        footer = QLabel("Click any button to launch a measurement script")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #888888; font-style: italic;")
        layout.addWidget(footer)

        self.setLayout(layout)

    def run_script(self, script_module, kind="subprocess"):
        if kind == "in_process":
            self._launch_in_process(script_module)
            return
        if kind == "action":
            self._launch_action(script_module)
            return
        thread = ScriptRunner(script_module, kind)
        self.threads.append(thread)
        thread.start()

    def _launch_in_process(self, script_module):
        try:
            module = importlib.import_module(script_module)
            window = module.MainWindow()
        except Exception:
            log.exception("Failed to launch %s in-process", script_module)
            return
        self.child_windows.append(window)
        window.show()

    def _launch_action(self, script_module):
        global _running_action
        if _running_action is not None:
            log.warning("Cannot start %s: %s is already running", script_module, _running_action)
            return
        busy_window = any_window_running()
        if busy_window is not None:
            log.warning("Cannot start %s: measurement in %s is running", script_module, busy_window)
            return
        label = script_module.rsplit(".", 1)[-1]
        runner = ActionRunner(script_module, label)
        _running_action = label
        runner.finished.connect(lambda r=runner: self._action_finished(r))
        self.threads.append(runner)
        runner.start()

    def _action_finished(self, runner):
        global _running_action
        _running_action = None
        try:
            self.threads.remove(runner)
        except ValueError:
            pass

    def open_data(self):
        # No parent: keep the launcher's dark stylesheet from cascading into the
        # dialog, so it matches the look of Pymeasure's stock Open dialog.
        dialog = CrossProcedureResultsDialog()
        dialog.setWindowTitle("Open results file")
        if not dialog.exec():
            return
        filenames = dialog.selectedFiles()
        if not filenames:
            return
        # Group selected files by window class so multiple files from the same
        # procedure stack as curves in a single window, matching Pymeasure's
        # native Open behavior.
        windows: dict[type, QWidget] = {}
        for filename in filenames:
            try:
                _, window_class = read_procedure_class(filename)
            except ValueError as e:
                QMessageBox.warning(self, "Cannot open file", str(e))
                continue
            window = windows.get(window_class)
            if window is None:
                try:
                    window = window_class()
                except Exception:
                    log.exception("Failed to construct %s for %s", window_class.__name__, filename)
                    QMessageBox.warning(
                        self,
                        "Cannot open file",
                        f"Failed to construct {window_class.__name__}. See logs for details.",
                    )
                    continue
                self.child_windows.append(window)
                window.show()
                windows[window_class] = window
            try:
                window.load_experiment_from_file(filename)
            except Exception:
                log.exception("Failed to load %s into %s", filename, window_class.__name__)
                QMessageBox.warning(
                    self,
                    "Cannot open file",
                    f"Failed to load data from {filename}. See logs for details.",
                )


def main():
    setup_file_logging("logs")
    # Match the locale that run_app() sets for standalone procedure runs so
    # in-process windows see dot-decimal input parsing too.
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QApplication(sys.argv)

    launcher = Launcher()
    launcher.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
