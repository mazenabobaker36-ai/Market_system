import base64
import hashlib
import hmac
import json
import os
import platform
import secrets
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from utils.paths import DATA_DIR


@dataclass(frozen=True)
class LicenseState:
    status: str
    message: str = ""


class LicenseManager:
    """Persists license data and applies the three-day offline policy."""

    VERIFY_URL = "https://preeminent-truffle-0ea26e.netlify.app/api/v1/license/verify"
    OFFLINE_GRACE_SECONDS = 3 * 24 * 60 * 60
    REQUEST_TIMEOUT = 15

    def __init__(self, path: Optional[Path] = None, verify_url: Optional[str] = None):
        self.path = path or (DATA_DIR / "license.dat")
        self.verify_url = verify_url or os.environ.get("POS_LICENSE_VERIFY_URL", self.VERIFY_URL)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def hardware_id() -> str:
        parts = [platform.system(), platform.machine(), platform.node()]
        machine_id = Path("/etc/machine-id")
        if machine_id.exists():
            parts.append(machine_id.read_text(encoding="utf-8").strip())
        parts.append(str(uuid.getnode()))
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def _encryption_key(self) -> bytes:
        seed = "|".join(
            [self.hardware_id(), platform.platform(), os.environ.get("COMPUTERNAME", "")]
        ).encode("utf-8")
        return hashlib.sha256(seed).digest()

    def _crypt(self, value: bytes, nonce: bytes) -> bytes:
        key = self._encryption_key()
        stream = bytearray()
        counter = 0
        while len(stream) < len(value):
            stream.extend(hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest())
            counter += 1
        return bytes(a ^ b for a, b in zip(value, stream))

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        raw = base64.b64decode(self.path.read_bytes(), validate=True)
        if len(raw) < 49:
            raise ValueError("License file is invalid")
        nonce, signature, encrypted = raw[:16], raw[16:48], raw[48:]
        expected = hmac.new(self._encryption_key(), nonce + encrypted, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("License file integrity check failed")
        return json.loads(self._crypt(encrypted, nonce).decode("utf-8"))

    def _write(self, data: Dict[str, Any]) -> None:
        nonce = secrets.token_bytes(16)
        encrypted = self._crypt(json.dumps(data, separators=(",", ":")).encode("utf-8"), nonce)
        signature = hmac.new(self._encryption_key(), nonce + encrypted, hashlib.sha256).digest()
        encoded = base64.b64encode(nonce + signature + encrypted)
        fd, temp_name = tempfile.mkstemp(prefix="license-", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        except OSError:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
            raise

    def has_local_license(self) -> bool:
        data = self._read()
        return bool(data.get("store_id") and data.get("license_key") and data.get("token"))

    def verify(self, store_id: str, license_key: str) -> LicenseState:
        payload = {
            "store_id": store_id.strip(),
            "license_key": license_key.strip(),
            "hardware_id": self.hardware_id(),
        }
        response = requests.post(self.verify_url, json=payload, timeout=self.REQUEST_TIMEOUT)
        response.raise_for_status()
        body = response.json()
        status = str(body.get("status", "")).lower()
        if status not in {"active", "expired", "blocked"}:
            raise ValueError("The licensing server returned an invalid status")
        if status == "active":
            token = body.get("token")
            if not token:
                raise ValueError("The licensing server did not return a token")
            data = self._read()
            data.update(
                {
                    "store_id": payload["store_id"],
                    "license_key": payload["license_key"],
                    "token": str(token),
                    "last_online_at": int(time.time()),
                    "offline_started_at": None,
                }
            )
            self._write(data)
        else:
            self._write({**self._read(), "last_status": status})
        return LicenseState(status)

    def check_offline(self) -> LicenseState:
        data = self._read()
        if not data.get("token"):
            return LicenseState("missing")
        now = int(time.time())
        last_online = int(data.get("last_online_at", 0))
        if last_online and now - last_online <= self.OFFLINE_GRACE_SECONDS:
            if not data.get("offline_started_at"):
                data["offline_started_at"] = now
                self._write(data)
            return LicenseState("active", "offline grace period")
        return LicenseState("offline_expired")

    def stored_credentials(self) -> Optional[tuple[str, str]]:
        data = self._read()
        if data.get("store_id") and data.get("license_key"):
            return str(data["store_id"]), str(data["license_key"])
        return None

    def stored_token(self) -> str:
        return str(self._read().get("token") or "")
