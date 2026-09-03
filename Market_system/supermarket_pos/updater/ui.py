import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QLabel, QProgressDialog, QVBoxLayout

from .worker import UpdateWorker


class UpdateDialog(QProgressDialog):
    """Checks and stages an update before the current process is replaced."""

    def __init__(self, store_id: str, current_version: str, parent=None):
        super().__init__(parent)
        self.worker = UpdateWorker(store_id, current_version, parent=self)
        self.package_path = None
        self.latest_version = None
        self.setWindowTitle("تحديث نظام السوبرماركت")
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setRange(0, 100)
        self.setValue(0)
        self.setAutoClose(False)
        self.setAutoReset(False)
        self.setCancelButtonText("إلغاء")
        self.setLabelText("جارٍ التحقق من وجود تحديث...")
        self.worker.no_update.connect(self._no_update)
        self.worker.update_available.connect(self._available)
        self.worker.progress.connect(self.setValue)
        self.worker.downloaded.connect(self._downloaded)
        self.worker.failed.connect(self._failed)
        self.canceled.connect(self._cancel_download)

    def start(self):
        self.worker.start()

    def _no_update(self, version):
        self.setLabelText(f"التطبيق محدث بالفعل (الإصدار {version})")
        self.done(QDialog.Rejected)

    def _available(self, version):
        self.latest_version = version
        self.setLabelText(f"جارٍ تنزيل الإصدار {version}...")

    def _downloaded(self, package_path, version):
        self.package_path = package_path
        self.latest_version = version
        self.setLabelText("اكتمل التنزيل، جارٍ بدء التحديث...")
        self.accept()

    def _failed(self, message):
        self.setLabelText(f"تعذر التحديث: {message}")
        self.done(QDialog.Rejected)

    def _cancel_download(self):
        if self.worker.isRunning():
            self.worker.requestInterruption()

    def closeEvent(self, event):
        if self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(2000)
        super().closeEvent(event)

    def launch_updater(self) -> None:
        if not self.package_path:
            raise RuntimeError("No update package was downloaded")
        app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
        current_executable = Path(sys.executable).resolve()
        if getattr(sys, "frozen", False):
            updater_command = app_dir / "updater.exe"
            if not updater_command.exists():
                raise RuntimeError("Updater helper is not installed")
            command = [
                str(updater_command),
                "--pid", str(os.getpid()),
                "--package", self.package_path,
                "--app-dir", str(app_dir),
                "--executable", str(current_executable),
            ]
        else:
            updater_script = Path(__file__).with_name("updater.py")
            command = [
                sys.executable,
                str(updater_script),
                "--pid", str(os.getpid()),
                "--package", self.package_path,
                "--app-dir", str(app_dir),
                "--executable", str(current_executable),
            ]
        subprocess.Popen(command, start_new_session=True, close_fds=True)
