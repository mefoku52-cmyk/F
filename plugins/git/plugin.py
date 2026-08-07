import os
import subprocess
from typing import Any, Dict, List

from core.collector import FileInfo
from core.finding import Finding, Severity
from core.plugin_manager import Plugin


class GitPlugin(Plugin):
    @property
    def name(self) -> str:
        return "git"

    def supports(self, project_path: str, files: List[FileInfo]) -> bool:
        return os.path.isdir(os.path.join(project_path, ".git"))

    def analyze(self, project_path: str, files: List[FileInfo]) -> List[Finding]:
        findings: List[Finding] = []

        branch = self._run_git(project_path, ["branch", "--show-current"])
        if branch:
            findings.append(
                Finding(
                    plugin=self.name,
                    severity=Severity.INFO,
                    message=f"Aktuálna vetva: {branch}",
                    location=project_path,
                    confidence=1.0,
                    metadata={"branch": branch},
                )
            )

        uncommitted = self._has_uncommitted(project_path)
        if uncommitted:
            findings.append(
                Finding(
                    plugin=self.name,
                    severity=Severity.MEDIUM,
                    message="Nepotvrdené zmeny v repozitári",
                    location=project_path,
                    confidence=0.9,
                )
            )

        contributors = self._get_contributors(project_path)
        if len(contributors) > 10:
            findings.append(
                Finding(
                    plugin=self.name,
                    severity=Severity.INFO,
                    message=f"Veľa prispievateľov: {len(contributors)}",
                    location=project_path,
                    confidence=0.8,
                    metadata={"contributor_count": len(contributors)},
                )
            )

        return findings

    def _run_git(self, cwd: str, args: List[str]) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", cwd] + args,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    def _has_uncommitted(self, cwd: str) -> bool:
        out = self._run_git(cwd, ["status", "--porcelain"])
        return bool(out.strip())

    def _get_contributors(self, cwd: str) -> List[Dict[str, str]]:
        out = self._run_git(cwd, ["shortlog", "-sn", "HEAD"])
        contributors = []
        for line in out.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                contributors.append({"commits": parts[0], "name": parts[1]})
        return contributors
