from PyQt5.QtCore import QThread, pyqtSignal
import requests

from .manager import LicenseManager, LicenseState


class LicenseCheckWorker(QThread):
    checked = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, manager: LicenseManager, store_id: str = "", license_key: str = "",
                 interval_seconds: int = 12 * 60 * 60, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.store_id = store_id
        self.license_key = license_key
        self.interval_seconds = interval_seconds
        self._stopping = False

    def run(self):
        first_check = True
        while not self._stopping:
            if self.store_id and self.license_key:
                try:
                    state = self.manager.verify(self.store_id, self.license_key)
                except (requests.RequestException, ValueError, OSError) as exc:
                    try:
                        state = self.manager.check_offline()
                    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as offline_exc:
                        self.failed.emit(str(offline_exc))
                        state = LicenseState("error", str(exc))
                    if state.status not in {"active"}:
                        self.failed.emit(str(exc))
                    self.checked.emit(state)
                else:
                    self.checked.emit(state)
            if not first_check:
                remaining = self.interval_seconds
                while remaining > 0 and not self._stopping and not self.isInterruptionRequested():
                    self.msleep(min(remaining, 1) * 1000)
                    remaining -= 1
            first_check = False

    def stop(self):
        self._stopping = True
        self.requestInterruption()
