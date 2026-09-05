import re
from typing import Tuple


def normalize_version(version: str) -> Tuple[int, ...]:
    values = re.findall(r"\d+", str(version or ""))
    if not values:
        raise ValueError(f"Invalid application version: {version!r}")
    return tuple(int(value) for value in values[:4])


def is_newer(latest_version: str, current_version: str) -> bool:
    latest = normalize_version(latest_version)
    current = normalize_version(current_version)
    width = max(len(latest), len(current))
    return latest + (0,) * (width - len(latest)) > current + (0,) * (width - len(current))
