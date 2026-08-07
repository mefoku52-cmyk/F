import re
from typing import Any, Dict, List, Set

from core.collector import FileInfo
from core.finding import Finding, Severity
from core.plugin_manager import Plugin

DEFAULT_PATTERNS = {
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "aws_secret_key": r"""['"][0-9a-zA-Z/+]{40}['"]""",
    "generic_api_key": r"""(?i)(api[_-]?key|apikey)\s*[:=]\s*['"][a-z0-9_\-]{16,}['"]""",
    "private_key": r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----",
    "password_assignment": r"""(?i)(password|passwd|pwd)\s*[:=]\s*['"][^'"]{4,}['"]""",
    "token": r"""(?i)(token|bearer)\s*[:=]\s*['"][a-z0-9_\-\.]{20,}['"]""",
    "github_token": r"ghp_[a-zA-Z0-9]{36}",
    "slack_token": r"xox[baprs]-[a-zA-Z0-9]{10,48}",
    "jwt": r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*",
}

TEXT_EXTENSIONS = {
    ".py", ".sh", ".bash", ".zsh", ".kt", ".java", ".xml", ".md",
    ".txt", ".json", ".yaml", ".yml", ".gradle", ".kts", ".html",
    ".css", ".js", ".ts", ".ini", ".cfg", ".conf", ".env",
}

MAX_FILE_SIZE = 2_000_000


class SecretsPlugin(Plugin):
    @property
    def name(self) -> str:
        return "secrets"

    def supports(self, project_path: str, files: List[FileInfo]) -> bool:
        return any(f.ext in TEXT_EXTENSIONS for f in files)

    def analyze(self, project_path: str, files: List[FileInfo]) -> List[Finding]:
        findings: List[Finding] = []
        scanned_files = 0

        for f in files:
            if f.ext not in TEXT_EXTENSIONS:
                continue
            if f.size > MAX_FILE_SIZE:
                continue

            try:
                with open(f.path, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError:
                continue

            scanned_files += 1
            for secret_type, pattern in DEFAULT_PATTERNS.items():
                for match in re.finditer(pattern, content):
                    line_no = content[:match.start()].count("\n") + 1
                    findings.append(Finding(
                        plugin=self.name,
                        severity=Severity.CRITICAL if secret_type in ("private_key", "aws_secret_key") else Severity.HIGH,
                        message=f"Nájdený {secret_type}: {match.group()[:30]}...",
                        location=f"{f.rel_path}:{line_no}",
                        confidence=0.8,
                        metadata={
                            "type": secret_type,
                            "match": match.group()[:50] + "..." if len(match.group()) > 50 else match.group(),
                            "line": line_no,
                        },
                    ))

        return findings
