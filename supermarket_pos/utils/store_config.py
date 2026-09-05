import json
import os
from pathlib import Path


DEFAULT_STORE_NAME = "سوبرماركت الخير"


def get_config_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "MySupermarketPOS" / "config.json"
    return Path.home() / ".config" / "MySupermarketPOS" / "config.json"


def load_store_name() -> str:
    try:
        with get_config_path().open("r", encoding="utf-8-sig") as config_file:
            value = json.load(config_file).get("store_name", "")
        return str(value).strip() or DEFAULT_STORE_NAME
    except (OSError, ValueError, TypeError, AttributeError):
        return DEFAULT_STORE_NAME
