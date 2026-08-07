"""
Jednoduchý file-based cache pre AST výsledky a file metadata.
"""

import hashlib
import json
import os
import time
from typing import Any, Dict, Optional


def _cache_dir(config: Dict[str, Any]) -> str:
    return config.get("cache", {}).get("dir", "forensicsuite_cache")


def _cache_enabled(config: Dict[str, Any]) -> bool:
    return config.get("cache", {}).get("enabled", True)


def _cache_ttl(config: Dict[str, Any]) -> int:
    return config.get("cache", {}).get("ttl_seconds", 3600)


def _file_hash(path: str) -> str:
    try:
        stat = os.stat(path)
        raw = f"{path}:{stat.st_size}:{stat.st_mtime}"
        return hashlib.sha256(raw.encode()).hexdigest()
    except OSError:
        return ""


def get_cached(path: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not _cache_enabled(config):
        return None
    cdir = _cache_dir(config)
    key = _file_hash(path)
    if not key:
        return None
    cache_file = os.path.join(cdir, f"{key}.json")
    if not os.path.isfile(cache_file):
        return None
    try:
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime > _cache_ttl(config):
            return None
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def set_cached(path: str, data: Dict[str, Any], config: Dict[str, Any]) -> None:
    if not _cache_enabled(config):
        return
    cdir = _cache_dir(config)
    os.makedirs(cdir, exist_ok=True)
    key = _file_hash(path)
    if not key:
        return
    cache_file = os.path.join(cdir, f"{key}.json")
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass
