import importlib
import logging
import subprocess
import sys

from qtpy.QtCore import QLocale, Qt, QThread
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements import reader
from probe_station.measurements.pymeasure_base import (
    any_window_running,
    register_busy_predicate,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

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
            logger.exception(f"Error running {self.script_module}: {e}")


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
            logger.exception("Error running action %s", self.script_module)


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
            [
                (
                    "📊 IV Sweep (SMU)",
                    "probe_station.measurements.smu.iv_sweep",
                    "#D1B122",
                    "in_process",
                ),
                (
                    "📊 Fast IV Sweep (WGFMU)",
                    "probe_station.measurements.wgfmu.iv_sweep",
                    "#2196F3",
                    "in_process",
                ),
                (
                    "📊 IV Sweep (SPGU) - experimental",
                    "probe_station.measurements.spgu.cycling_with_current",
                    "#4CAF50",
                    "in_process",
                ),
            ],
            [
                (
                    "🔄 Cycling (WGFMU)",
                    "probe_station.measurements.wgfmu.cycling",
                    "#2196F3",
                    "in_process",
                ),
                ("🔄 Cycling (SPGU)", "probe_station.measurements.spgu.cycling", "#4CAF50", "in_process"),
            ],
            # A nested list lays its buttons out in a single horizontal row.
            [
                (
                    "📊 CV Sweep\n(CMU)",
                    "probe_station.measurements.cmu.cv_sweep",
                    "#C224BA",
                    "in_process",
                ),
                (
                    "📊 Quasi-static CV Sweep\n(SMU) - experimental",
                    "probe_station.measurements.smu.quasistatic_cv",
                    "#D1B122",
                    "in_process",
                ),
                (
                    "🛠 Offset Cancel\n(open tips)",
                    "probe_station.measurements.smu.quasistatic_cv_offset",
                    "#D1B122",
                    "in_process",
                ),
            ],
            [
                (
                    "📊 Ids (Vg) (SMU)",
                    "probe_station.measurements.smu.fet_ids_vg",
                    "#D1B122",
                    "in_process",
                ),
                (
                    "📊 Ids (Vds) (SMU)",
                    "probe_station.measurements.smu.fet_ids_vds",
                    "#D1B122",
                    "in_process",
                ),
                (
                    "📊 Ids (Vg) (WGFMU)",
                    "probe_station.measurements.wgfmu.fet_ids_vg",
                    "#2196F3",
                    "in_process",
                ),
                (
                    "📊 Ids @ DC bias (WGFMU) - experimental",
                    "probe_station.measurements.wgfmu.fet_ids_dc",
                    "#2196F3",
                    "in_process",
                ),
            ],
            ("✨ Вжух", "probe_station.measurements.magic", "#575656FF", "action"),
        ]

        def make_button(script_data):
            if len(script_data) == 4:
                name, module, color, kind = script_data
            else:
                name, module, color = script_data
                kind = "subprocess"

            button = ModernButton(name, color)
            button.clicked.connect(lambda checked, m=module, k=kind: self.run_script(m, k))
            return button

        for entry in scripts:
            if isinstance(entry, list):  # a list of specs becomes one horizontal row
                row = QHBoxLayout()
                for spec in entry:
                    row.addWidget(make_button(spec))
                layout.addLayout(row)
            else:
                layout.addWidget(make_button(entry))

        layout.addStretch()

        reader_separator = QFrame()
        reader_separator.setFrameShape(QFrame.HLine)
        reader_separator.setStyleSheet("background-color: #555555; height: 2px;")
        layout.addWidget(reader_separator)

        open_data_button = ModernButton("📁 Open data…", "#575656FF")
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
            logger.exception("Failed to launch %s in-process", script_module)
            return
        self.child_windows.append(window)
        window.show()

    def _launch_action(self, script_module):
        global _running_action
        if _running_action is not None:
            logger.warning("Cannot start %s: %s is already running", script_module, _running_action)
            return
        busy_window = any_window_running()
        if busy_window is not None:
            logger.warning("Cannot start %s: measurement in %s is running", script_module, busy_window)
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
        reader.open_data(self, self.child_windows)


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
