import os
import time
from typing import Any, Dict, List

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from database.db_manager import DBManager


class SyncWorker(QThread):
    """Silent, durable sales and telemetry synchronizer.

    All database work happens through fresh SQLite connections in DBManager.
    A failed request leaves invoices unsynced so the next retry cannot lose data.
    """

    sync_succeeded = pyqtSignal(int)
    heartbeat_succeeded = pyqtSignal()
    sync_error = pyqtSignal(str)

    def __init__(
        self,
        db: DBManager,
        store_id: str,
        token: str = "",
        base_url: str = "https://preeminent-truffle-0ea26e.netlify.app/api/v1",
        batch_size: int = 50,
        sync_interval_seconds: int = 15 * 60,
        parent=None,
    ):
        super().__init__(parent)
        self.db = db
        self.store_id = store_id.strip()
        self.token = token.strip()
        self.base_url = os.environ.get("POS_SYNC_BASE_URL", base_url).rstrip("/")
        self.batch_size = max(1, int(batch_size))
        self.sync_interval_seconds = max(1, int(sync_interval_seconds))
        self._stopping = False
        self._backoff_seconds = 1

    def _headers(self) -> Dict[str, str]:
        headers = {"X-Store-ID": self.store_id, "Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> requests.Response:
        response = requests.post(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        if response.status_code != 200:
            raise requests.HTTPError(f"Unexpected sync response status: {response.status_code}")
        return response

    def _sync_sales(self) -> int:
        total_synced = 0
        while not self._stopping:
            sales = self.db.get_pending_sales(self.batch_size)
            if not sales:
                return total_synced
            self._post("sync/sales", {"sales": sales})
            count = self.db.mark_sales_synced([sale["id"] for sale in sales])
            total_synced += count
            if count != len(sales):
                raise RuntimeError("The local sync acknowledgement was incomplete")
        return total_synced

    def _send_heartbeat(self) -> None:
        self._post("sync/heartbeat", self.db.get_sync_metrics())

    def _wait(self, seconds: int) -> None:
        for _ in range(seconds):
            if self._stopping or self.isInterruptionRequested():
                return
            self.msleep(1000)

    def run(self):
        while not self._stopping and not self.isInterruptionRequested():
            try:
                synced = self._sync_sales()
                self._send_heartbeat()
                self._backoff_seconds = 1
                if synced:
                    self.sync_succeeded.emit(synced)
                self.heartbeat_succeeded.emit()
                self._wait(self.sync_interval_seconds)
            except (requests.RequestException, OSError, ValueError, RuntimeError) as exc:
                self.sync_error.emit(str(exc))
                self._wait(self._backoff_seconds)
                self._backoff_seconds = min(self._backoff_seconds * 2, 30 * 60)

    def stop(self):
        self._stopping = True
        self.requestInterruption()
