import os
import re
from typing import Any, Dict, List

from core.collector import FileInfo
from core.finding import Finding, Severity
from core.plugin_manager import Plugin

SHELL_EXTENSIONS = {".sh", ".bash", ".zsh", ".ksh"}
DANGEROUS_PATTERNS = {
    "eval": r"\beval\s",
    "exec": r"\bexec\s",
    "rm_rf": r"rm\s+-[a-zA-Z]*f",
    "curl_pipe": r"curl\s+.*\|\s*(ba)?sh",
    "wget_pipe": r"wget\s+.*\|\s*(ba)?sh",
    "sudo": r"\bsudo\b",
    "chmod_777": r"chmod\s+.*777",
    "hardcoded_path": r"/data/data/com\.termux|/sdcard/|/system/",
}


class ShellPlugin(Plugin):
    @property
    def name(self) -> str:
        return "shell"

    def supports(self, project_path: str, files: List[FileInfo]) -> bool:
        return any(f.ext in SHELL_EXTENSIONS for f in files)

    def analyze(self, project_path: str, files: List[FileInfo]) -> List[Finding]:
        findings: List[Finding] = []
        scripts_analyzed = 0

        for f in files:
            if f.ext not in SHELL_EXTENSIONS:
                continue
            try:
                with open(f.path, "r", encoding="utf-8", errors="ignore") as fh:
                    lines = fh.readlines()
            except OSError:
                continue

            scripts_analyzed += 1
            has_shebang = lines and lines[0].startswith("#!/") if lines else False

            for line_no, line in enumerate(lines, 1):
                for danger_type, pattern in DANGEROUS_PATTERNS.items():
                    if re.search(pattern, line):
                        findings.append(
                            Finding(
                                plugin=self.name,
                                severity=(
                                    Severity.CRITICAL
                                    if danger_type
                                    in ("eval", "exec", "curl_pipe", "wget_pipe")
                                    else Severity.HIGH
                                ),
                                message=f"Nebezpečný príkaz: {danger_type}",
                                location=f"{f.rel_path}:{line_no}",
                                confidence=0.7,
                                metadata={
                                    "type": danger_type,
                                    "content": line.strip()[:100],
                                },
                            )
                        )

            if not has_shebang and f.ext == ".sh":
                findings.append(
                    Finding(
                        plugin=self.name,
                        severity=Severity.LOW,
                        message=f"Chýbajúci shebang v {f.rel_path}",
                        location=f.rel_path,
                        confidence=0.9,
                    )
                )

        return findings
