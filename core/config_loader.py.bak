"""
Načítavanie konfigurácie s fallbackom:
  1. --config argument (YAML alebo JSON)
  2. config/default.yaml (ak je PyYAML nainštalovaný)
  3. Hardcoded defaults (vždy funguje)
"""
import json
import os
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "exclude_dirs": [
        ".git", "__pycache__", ".venv", "venv", "node_modules",
        ".gradle", "build", ".idea", ".pytest_cache", "dist",
        "*.egg-info", "forensicsuite_report", "forensicsuite_cache",
    ],
    "scoring_weights": {
        "maintainability": {
            "complexity_penalty_cap": 40,
            "duplicate_penalty_cap": 20,
            "unused_imports_penalty_cap": 15,
        },
        "architecture": {
            "cyclic_import_penalty_per_cycle": 15,
            "orphaned_file_penalty_per_file": 2,
        },
        "security": {
            "vuln_penalty_per_cve": 20,
            "secret_penalty_per_finding": 10,
            "secret_penalty_cap": 50,
        },
    },
    "cve_check": {
        "enabled": True,
        "timeout_seconds": 10,
    },
    "secrets": {
        "enabled": True,
        "patterns": {
            "aws_access_key": r"AKIA[0-9A-Z]{16}",
            "aws_secret_key": r"""['"][0-9a-zA-Z/+]{40}['"]""",
            "generic_api_key": r"""(?i)(api[_-]?key|apikey)\s*[:=]\s*['"][a-z0-9_\-]{16,}['"]""",
            "private_key": r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----",
            "password_assignment": r"""(?i)(password|passwd|pwd)\s*[:=]\s*['"][^'"]{4,}['"]""",
            "token": r"""(?i)(token|bearer)\s*[:=]\s*['"][a-z0-9_\-\.]{20,}['"]""",
        },
    },
    "cache": {
        "enabled": True,
        "dir": "forensicsuite_cache",
        "ttl_seconds": 3600,
    },
    "server": {
        "host": "127.0.0.1",
        "port": 8765,
    },
}


def load_config(path: str = "") -> Dict[str, Any]:
    config = _deep_copy(DEFAULT_CONFIG)
    candidates = []
    if path:
        candidates.append(path)
    candidates.extend(["config/default.yaml", "config/default.json"])

    for candidate in candidates:
        if not os.path.isfile(candidate):
            continue
        ext = os.path.splitext(candidate)[1].lower()
        try:
            if ext in (".yaml", ".yml"):
                config = _merge(config, _load_yaml(candidate))
            elif ext == ".json":
                with open(candidate, "r", encoding="utf-8") as f:
                    config = _merge(config, json.load(f))
        except Exception:
            continue
        break
    return config


def _deep_copy(d: Dict[str, Any]) -> Dict[str, Any]:
    import copy
    return copy.deepcopy(d)


def _merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    result = _deep_copy(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml(path: str) -> Dict[str, Any]:
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return _naive_yaml_parse(path)


def _naive_yaml_parse(path: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    current_key = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if not stripped.strip() or stripped.strip().startswith("#"):
                continue
            if not stripped.startswith(" ") and not stripped.startswith("\t"):
                if ":" in stripped:
                    key, val = stripped.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    if val.startswith("[") and val.endswith("]"):
                        result[key] = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
                    elif val:
                        result[key] = val.strip('"').strip("'")
                    else:
                        result[key] = {}
                        current_key = key
                else:
                    current_key = None
            elif current_key is not None and isinstance(result.get(current_key), dict):
                if ":" in stripped:
                    sub_key, sub_val = stripped.strip().split(":", 1)
                    sub_val = sub_val.strip()
                    if sub_val.startswith("[") and sub_val.endswith("]"):
                        result[current_key][sub_key.strip()] = [v.strip().strip('"').strip("'") for v in sub_val[1:-1].split(",")]
                    else:
                        try:
                            result[current_key][sub_key.strip()] = int(sub_val)
                        except ValueError:
                            try:
                                result[current_key][sub_key.strip()] = float(sub_val)
                            except ValueError:
                                result[current_key][sub_key.strip()] = sub_val.strip('"').strip("'")
    return result
