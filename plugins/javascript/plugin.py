import json
import os
from typing import Any, Dict, List

from core.collector import FileInfo
from core.finding import Finding, Severity
from core.plugin_manager import Plugin
from core.tool_runner import ToolRunner


class JavaScriptPlugin(Plugin):
    @property
    def name(self) -> str:
        return "javascript"

    def supports(self, project_path: str, files: List[FileInfo]) -> bool:
        js_extensions = {".js", ".jsx", ".ts", ".tsx"}
        return any(f.ext in js_extensions for f in files)

    def analyze(self, project_path: str, files: List[FileInfo]) -> List[Finding]:
        findings: List[Finding] = []
        runner = ToolRunner(timeout=60)

        has_package = os.path.isfile(os.path.join(project_path, "package.json"))
        has_eslintrc = any(
            os.path.isfile(os.path.join(project_path, f))
            for f in [".eslintrc", ".eslintrc.json", ".eslintrc.js", ".eslintrc.yaml", ".eslintrc.yml"]
        )

        if not has_package and not has_eslintrc:
            findings.append(Finding(
                plugin=self.name,
                severity=Severity.INFO,
                message="Chýba package.json alebo .eslintrc – preskočené",
                location=project_path,
                confidence=1.0,
            ))
            return findings

        cmd = self._build_command(project_path)
        if not cmd:
            findings.append(Finding(
                plugin=self.name,
                severity=Severity.INFO,
                message="ESLint nie je nainštalovaný – preskočené",
                location=project_path,
                confidence=1.0,
            ))
            return findings

        rc, stdout, stderr = runner.run(cmd, cwd=project_path, timeout=60)

        if rc != 0 and stdout.strip() == "":
            findings.append(Finding(
                plugin=self.name,
                severity=Severity.MEDIUM,
                message=f"ESLint zlyhal: {stderr[:100]}",
                location=project_path,
                confidence=0.7,
                metadata={"stderr": stderr[:200]},
            ))
            return findings

        try:
            data = json.loads(stdout) if stdout else []
        except json.JSONDecodeError:
            findings.append(Finding(
                plugin=self.name,
                severity=Severity.MEDIUM,
                message="ESLint vrátil neplatný JSON",
                location=project_path,
                confidence=0.5,
            ))
            return findings

        for file_result in data:
            file_path = file_result.get("filePath", "")
            rel_path = os.path.relpath(file_path, project_path) if file_path else ""
            for msg in file_result.get("messages", []):
                severity = self._map_severity(msg.get("severity", 0))
                line = msg.get("line", 0)
                column = msg.get("column", 0)
                rule_id = msg.get("ruleId", "unknown")
                message = msg.get("message", "")

                findings.append(Finding(
                    plugin=self.name,
                    severity=severity,
                    message=f"[{rule_id}] {message[:100]}",
                    location=f"{rel_path}:{line}" if rel_path else "",
                    confidence=0.85,
                    metadata={
                        "rule_id": rule_id,
                        "line": line,
                        "column": column,
                        "severity_original": msg.get("severity"),
                        "fix": msg.get("fix", {}),
                    },
                ))

        return findings

    def _build_command(self, project_path: str) -> List[str]:
        if self._check_npx():
            js_files = self._find_js_files(project_path)
            if js_files:
                return ["npx", "eslint", "--format", "json", "--no-eslintrc"] + js_files
            else:
                return ["npx", "eslint", "--format", "json", "--no-eslintrc", "."]

        if ToolRunner().check_installed("eslint"):
            return ["eslint", "--format", "json", "."]

        return []

    def _check_npx(self) -> bool:
        return ToolRunner().check_installed("npx")

    def _find_js_files(self, project_path: str) -> List[str]:
        extensions = {".js", ".jsx", ".ts", ".tsx"}
        files = []
        for root, dirs, names in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in ["node_modules", ".git", "__pycache__"]]
            for name in names:
                ext = os.path.splitext(name)[1].lower()
                if ext in extensions:
                    files.append(os.path.join(root, name))
                    if len(files) >= 100:
                        return files
        return files

    def _map_severity(self, eslint_severity: int) -> Severity:
        if eslint_severity == 2:
            return Severity.HIGH
        elif eslint_severity == 1:
            return Severity.MEDIUM
        else:
            return Severity.INFO
