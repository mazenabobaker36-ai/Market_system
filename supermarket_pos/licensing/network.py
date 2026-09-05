import requests
from typing import Any, Dict, Optional


class NetworkManager:
    """Small HTTP client for desktop licensing calls."""

    BASE_URL = "https://preeminent-truffle-0ea26e.netlify.app/"

    def __init__(self, base_url: Optional[str] = None, timeout: int = 15):
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout

    def verify_license(
        self, store_id: str, license_key: str, hardware_id: str = ""
    ) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/api/v1/license/verify",
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
