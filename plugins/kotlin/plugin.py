import json
import os
import tempfile
from typing import Any, Dict, List

from core.collector import FileInfo
from core.finding import Finding, Severity
from core.plugin_manager import Plugin
from core.tool_runner import ToolRunner


class KotlinPlugin(Plugin):
    @property
    def name(self) -> str:
        return "kotlin"

    def supports(self, project_path: str, files: List[FileInfo]) -> bool:
        return any(f.ext == ".kt" for f in files)

    def analyze(self, project_path: str, files: List[FileInfo]) -> List[Finding]:
        findings: List[Finding] = []
        runner = ToolRunner(timeout=60)

        # Kontrola, či je detekt nainštalovaný
        if not runner.check_installed("detekt"):
            findings.append(Finding(
                plugin=self.name,
                severity=Severity.INFO,
                message="detekt nie je nainštalovaný – preskočené",
                location=project_path,
                confidence=1.0,
            ))
            return findings

        # Nájdi .kt súbory
        kt_files = runner.find_project_files(project_path, [".kt"])
        if not kt_files:
            return findings

        # Spustíme detekt s výstupom v JSON
        cmd = [
            "detekt",
            "--input", project_path,
            "--output", "-",
            "--report", "json:detekt_report.json",
            "--parallel",
        ]

        rc, stdout, stderr = runner.run(cmd, cwd=project_path, timeout=60)

        # Detekt vracia 0 aj keď nájde problémy – skontrolujeme, či existuje report
        report_path = os.path.join(project_path, "detekt_report.json")
        if os.path.isfile(report_path):
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                os.unlink(report_path)

                # Parsovanie detekt výstupu
                for file_path, issues in data.get("files", {}).items():
                    for issue in issues.get("issues", []):
                        severity = self._map_severity(issue.get("severity", "Info"))
                        findings.append(Finding(
                            plugin=self.name,
                            severity=severity,
                            message=f"[{issue.get('id', 'unknown')}] {issue.get('message', '')[:100]}",
                            location=f"{os.path.relpath(file_path, project_path)}:{issue.get('line', 1)}",
                            confidence=0.85,
                            metadata={
                                "rule": issue.get("id"),
                                "severity_original": issue.get("severity"),
                                "line": issue.get("line"),
                            },
                        ))
            except (json.JSONDecodeError, OSError):
                pass

        return findings

    def _map_severity(self, detekt_severity: str) -> Severity:
        mapping = {
            "Critical": Severity.CRITICAL,
            "High": Severity.HIGH,
            "Medium": Severity.MEDIUM,
            "Low": Severity.LOW,
            "Info": Severity.INFO,
        }
        return mapping.get(detekt_severity, Severity.INFO)
