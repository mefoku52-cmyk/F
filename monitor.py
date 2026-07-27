#!/usr/bin/env python3
"""
Live monitoring daemon pre ForensicSuite.
Periodicky skenuje projekt a ukladá výsledky do histórie.
Použitie: python3 monitor.py --path . --interval 3600 --threshold 70
"""
import argparse
import os
import sys
import time
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.engine import ForensicEngine
from core.history import save_scan_history  # ak existuje


def notify(message: str):
    """Jednoduchá notifikácia cez Termux."""
    os.system(f'termux-notification --title "ForensicSuite" --content "{message}" 2>/dev/null || echo "[ALERT] {message}"')


def run_monitor(path: str, interval: int, threshold: float):
    print(f"🔴 Monitor spustený: {path}")
    print(f"   Interval: {interval}s | Threshold: {threshold}")
    print(f"   Stlač Ctrl+C pre ukončenie")
    print("-" * 50)

    scan_count = 0
    while True:
        scan_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Sken #{scan_count}...")

        try:
            engine = ForensicEngine(path)
            result = engine.run()

            scores = result.get("scores", {})
            maint = scores.get("maintainability", {}).get("score", 100)
            arch = scores.get("architecture", {}).get("score", 100)
            sec = scores.get("security", {}).get("score", 100)
            min_score = min(maint, arch, sec)

            print(f"   Maintainability: {maint} | Architecture: {arch} | Security: {sec}")

            if min_score < threshold:
                alert_msg = f"Skóre kleslo pod {threshold}! Min: {min_score} (m:{maint} a:{arch} s:{sec})"
                print(f"   🚨 ALERT: {alert_msg}")
                notify(alert_msg)

            # Ulož do histórie
            try:
                from core.history import save_scan_history
                save_scan_history(result)
            except ImportError:
                pass

        except Exception as e:
            print(f"   ❌ Chyba: {e}")

        print(f"   Ďalší sken o {interval}s...")
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=".", help="Cesta k projektu")
    parser.add_argument("--interval", type=int, default=3600, help="Interval v sekundách")
    parser.add_argument("--threshold", type=float, default=70.0, help="Prahové skóre pre alert")
    args = parser.parse_args()

    try:
        run_monitor(args.path, args.interval, args.threshold)
    except KeyboardInterrupt:
        print("\n🛑 Monitor ukončený.")
