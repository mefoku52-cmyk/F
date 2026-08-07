import json
import os
from typing import Any, Dict, List

from core.collector import FileInfo
from core.finding import Finding, Severity
from core.plugin_manager import Plugin
from core.tool_runner import ToolRunner


class GoPlugin(Plugin):
    @property
    def name(self) -> str:
        return "go"

    def supports(self, project_path: str, files: List[FileInfo]) -> bool:
        return any(f.ext == ".go" for f in files)

    def analyze(self, project_path: str, files: List[FileInfo]) -> List[Finding]:
        findings: List[Finding] = []
        runner = ToolRunner(timeout=120)

        # 1. Skontrolujeme, či existuje go.mod
        if not os.path.isfile(os.path.join(project_path, "go.mod")):
            findings.append(
                Finding(
                    plugin=self.name,
                    severity=Severity.INFO,
                    message="Chýba go.mod – preskočené",
                    location=project_path,
                    confidence=1.0,
                )
            )
            return findings

        # 2. Skontrolujeme, či je nainštalovaný golangci-lint
        if not runner.check_installed("golangci-lint"):
            findings.append(
                Finding(
                    plugin=self.name,
                    severity=Severity.INFO,
                    message="golangci-lint nie je nainštalovaný – preskočené",
                    location=project_path,
                    confidence=1.0,
                )
            )
            return findings

        # 3. Spustenie golangci-lint s JSON výstupom
        cmd = [
            "golangci-lint",
            "run",
            "--out-format",
            "json",
            "--issues-exit-code",
            "0",
            "./...",
        ]

        rc, stdout, stderr = runner.run(cmd, cwd=project_path, timeout=120)

        if rc != 0 and stdout.strip() == "":
            findings.append(
                Finding(
                    plugin=self.name,
                    severity=Severity.MEDIUM,
                    message=f"golangci-lint zlyhal: {stderr[:100]}",
                    location=project_path,
                    confidence=0.7,
                    metadata={"stderr": stderr[:200]},
                )
            )
            return findings

        # 4. Parsovanie JSON výstupu
        try:
            data = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            findings.append(
                Finding(
                    plugin=self.name,
                    severity=Severity.MEDIUM,
                    message="golangci-lint vrátil neplatný JSON",
                    location=project_path,
                    confidence=0.5,
                )
            )
            return findings

        # 5. Mapovanie na Finding
        issues = data.get("Issues", [])
        for issue in issues:
            file_path = issue.get("Pos", {}).get("Filename", "")
            rel_path = os.path.relpath(file_path, project_path) if file_path else ""
            line = issue.get("Pos", {}).get("Line", 1)
            column = issue.get("Pos", {}).get("Column", 1)
            severity = self._map_severity(issue.get("Severity", ""))
            rule_id = issue.get("FromLinter", "unknown")
            message = issue.get("Text", "")

            findings.append(
                Finding(
                    plugin=self.name,
                    severity=severity,
                    message=f"[{rule_id}] {message[:100]}",
                    location=f"{rel_path}:{line}" if rel_path else "",
                    confidence=0.85,
                    metadata={
                        "rule_id": rule_id,
                        "line": line,
                        "column": column,
                        "severity_original": issue.get("Severity"),
                        "source_lines": issue.get("SourceLines", [])[:3],
                    },
                )
            )

        return findings

    def _map_severity(self, golangci_severity: str) -> Severity:
        mapping = {
            "error": Severity.HIGH,
            "warning": Severity.MEDIUM,
            "info": Severity.INFO,
            "": Severity.INFO,
        }
        return mapping.get(golangci_severity.lower(), Severity.INFO)
