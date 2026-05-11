import importlib
import logging
import subprocess
import sys

from qtpy.QtCore import QLocale, Qt, QThread
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from probe_station.logging_setup import setup_file_logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


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
            ("✨ Вжух", "probe_station.measurements.magic", "#D1B122"),
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
