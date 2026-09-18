import os
from typing import Any, Dict, Optional

import requests


class NetworkManager:
    """Small HTTP client for desktop licensing calls."""

    BASE_URL = "https://preeminent-truffle-0ea26e.netlify.app/api/v1"

    def __init__(self, base_url: Optional[str] = None, timeout: int = 15):
        configured_url = base_url or os.getenv("API_BASE_URL", self.BASE_URL)
        self.base_url = configured_url.rstrip("/")
        self.timeout = timeout

    def verify_license(
        self, store_id: str, license_key: str, hardware_id: str = ""
    ) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/license/verify",
            json={
                "store_id": store_id.strip(),
                "license_key": license_key.strip(),
                "hardware_id": hardware_id,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") not in {"active", "expired", "blocked"}:
            raise ValueError("Invalid license status returned by server")
        return payload
