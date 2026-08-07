# flake8: noqa: E402
#!/usr/bin/env python3
"""
AI Post-processor pre ForensicSuite.
Pridá ai_analysis k existujúcemu report.json bez modifikácie engine/cli.
Použitie: python3 tools/ai_postprocess.py forensicsuite_report/report.json
"""

import json
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from plugins.ai_assistant.plugin import AIAssistantPlugin


def main():
    if len(sys.argv) < 2:
        print("Použitie: python3 tools/ai_postprocess.py <cesta/k/report.json>")
        sys.exit(1)

    report_path = sys.argv[1]
    if not os.path.isfile(report_path):
        print(f"Súbor neexistuje: {report_path}")
        sys.exit(1)

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    ai = AIAssistantPlugin()
    report["ai_analysis"] = ai.classify_findings(report)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    ai_data = report["ai_analysis"]
    print("=" * 50)
    print("AI ANALÝZA PRIDANÁ")
    print("=" * 50)
    print("Total findings:", ai_data.get("total_findings"))
    print("Likely real:   ", ai_data.get("likely_real"))
    print("Likely FP:     ", ai_data.get("likely_false_positive"))
    print("")
    print(ai_data.get("recommendation", "")[:200])
    print("")
    print("Uložené do:", report_path)


if __name__ == "__main__":
    main()
