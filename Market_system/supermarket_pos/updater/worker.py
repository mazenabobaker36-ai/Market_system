import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from .version import is_newer


class UpdateWorker(QThread):
    checking = pyqtSignal()
    no_update = pyqtSignal(str)
    update_available = pyqtSignal(str)
    progress = pyqtSignal(int)
    downloaded = pyqtSignal(str, str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        store_id: str,
        current_version: str,
        base_url: str = "https://preeminent-truffle-0ea26e.netlify.app/api/v1",
        parent=None,
    ):
        super().__init__(parent)
        self.store_id = store_id.strip()
        self.current_version = current_version
        self.base_url = os.environ.get("POS_UPDATE_BASE_URL", base_url).rstrip("/")

    def _version_info(self) -> Dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/app/check-update",
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        latest = str(payload.get("version") or payload.get("latest_version") or "")
        if not latest:
            raise ValueError("Version service did not return latest_version")
        return payload

    def run(self):
        self.checking.emit()
        try:
            info = self._version_info()
            latest = str(info["latest_version"])
            if not is_newer(latest, self.current_version):
                self.no_update.emit(latest)
                return
            package_url = str(info.get("download_url") or info.get("package_url") or "")
            if not package_url:
                raise ValueError("Version service did not return a download URL")
            self.update_available.emit(latest)
            suffix = ".exe" if package_url.lower().split("?")[0].endswith(".exe") else ".zip"
            fd, destination = tempfile.mkstemp(prefix="supermarket-pos-update-", suffix=suffix)
            os.close(fd)
            try:
                with requests.get(package_url, stream=True, timeout=30) as response:
                    response.raise_for_status()
                    total = int(response.headers.get("Content-Length") or 0)
                    received = 0
                    with open(destination, "wb") as package:
                        for chunk in response.iter_content(chunk_size=1024 * 128):
                            if self.isInterruptionRequested():
                                raise RuntimeError("Update download cancelled")
                            if chunk:
                                package.write(chunk)
                                received += len(chunk)
                                if total:
                                    self.progress.emit(min(100, int(received * 100 / total)))
                self.progress.emit(100)
                self.downloaded.emit(destination, latest)
            except Exception:
                Path(destination).unlink(missing_ok=True)
                raise
        except (requests.RequestException, OSError, ValueError, RuntimeError) as exc:
            self.failed.emit(str(exc))
