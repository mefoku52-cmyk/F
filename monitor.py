#!/usr/bin/env python3
import subprocess
import json
import os
from datetime import datetime


def check_metrics(project_path):
    """Monitoruje metriky projektu."""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "python_findings": 0,
        "secrets_findings": 0,
    }

    # Počítať dead code
    try:
        result = subprocess.run(
            ["vulture", project_path, "--min-confidence=80"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        metrics["dead_code_lines"] = len(result.stdout.split("\n")) - 1
    except (subprocess.TimeoutExpired, FileNotFoundError):
        metrics["dead_code_lines"] = -1

    # Počítať komplexitu
    try:
        result = subprocess.run(
            ["radon", "cc", project_path, "-a"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        metrics["complexity"] = result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        metrics["complexity"] = "N/A"

    # Uložiť históriu
    history_file = "metrics_history.json"
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except (json.JSONDecodeError, OSError):
            history = []

    history.append(metrics)

    try:
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
    except OSError:
        pass

    print(f"📊 Metriky uložené do {history_file}")
    return metrics


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "."
    check_metrics(path)
