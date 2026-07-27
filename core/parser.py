import os
from typing import Optional


def safe_read_text(path: str, max_bytes: int = 5_000_000) -> Optional[str]:
    try:
        size = os.path.getsize(path)
        if size > max_bytes:
            return None
        with open(path, "rb") as f:
            raw = f.read()
        if b"\x00" in raw[:1024]:
            return None
        return raw.decode("utf-8", errors="strict")
    except (UnicodeDecodeError, OSError):
        return None

