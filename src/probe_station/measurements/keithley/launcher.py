import logging
import sys

from pymeasure.display.Qt import QtWidgets
from qtpy.QtCore import QLocale, QObject, QThread, Signal
from qtpy.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from probe_station.logging_setup import setup_file_logging
from probe_station.measurements.keithley.device import connect_instrument, get_smu, set_smu

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

ADDRESS = "TCPIP0::192.168.81.20::inst0::INSTR"


class _ConnectWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, address: str):
        super().__init__()
        self.address = address

    def run(self):
        try:
            self.succeeded.emit(connect_instrument(self.address))
        except ConnectionError as e:
            self.failed.emit(str(e))


class LauncherWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keithley 2450 Launcher")
        self._windows: list[QWidget] = []
        self._thread: QThread | None = None

        self._address = QLineEdit(ADDRESS)
        self._address.setMinimumWidth(self._address.fontMetrics().horizontalAdvance(ADDRESS) + 20)
        self._status = QLabel("Disconnected")
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._toggle_connection)

        self._pund_btn = QPushButton("PUND measurement")
        self._pund_btn.setEnabled(False)
        self._pund_btn.clicked.connect(self._open_pund)

        address_row = QHBoxLayout()
        address_row.addWidget(QLabel("Address:"))
        address_row.addWidget(self._address)

        layout = QVBoxLayout()
        layout.addLayout(address_row)
        layout.addWidget(self._status)
        layout.addWidget(self._connect_btn)
        layout.addWidget(self._pund_btn)
        self.setLayout(layout)

    def _toggle_connection(self):
        try:
            smu = get_smu()
        except RuntimeError:
            smu = None

        if smu is None:
            self._connect_btn.setEnabled(False)
            self._status.setText("Connecting…")

            self._thread = QThread()
            self._worker = _ConnectWorker(self._address.text())
            self._worker.moveToThread(self._thread)
            self._thread.started.connect(self._worker.run)
            self._worker.succeeded.connect(self._on_connected)
            self._worker.failed.connect(self._on_connect_failed)
            self._worker.succeeded.connect(self._thread.quit)
            self._worker.failed.connect(self._thread.quit)
            self._thread.start()
        else:
            smu.adapter.close()
            set_smu(None)
            self._status.setText("Disconnected")
            self._connect_btn.setText("Connect")
            self._pund_btn.setEnabled(False)

    def _on_connected(self, smu):
        set_smu(smu)
        self._status.setText(f"Connected: {self._address.text()}")
        self._connect_btn.setText("Disconnect")
        self._connect_btn.setEnabled(True)
        self._pund_btn.setEnabled(True)

    def _on_connect_failed(self, message: str):
        self._status.setText("Disconnected")
        self._connect_btn.setEnabled(True)
        QMessageBox.critical(self, "Connection failed", message)

    def _open_pund(self):
        from probe_station.measurements.keithley.PUND_procedure import MainWindow

        window = MainWindow()
        window.show()
        self._windows.append(window)

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        try:
            get_smu().adapter.close()
            set_smu(None)
            log.info("Keithley disconnected")
        except RuntimeError:
            pass
        event.accept()


if __name__ == "__main__":
    setup_file_logging("logs")
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    app = QtWidgets.QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    app.exec()
