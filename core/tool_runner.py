import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple


class ToolRunner:
    """Jednotné rozhranie pre spúšťanie externých nástrojov."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def check_installed(self, tool: str) -> bool:
        """Overí, či je nástroj dostupný v PATH."""
        return shutil.which(tool) is not None

    def run(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Tuple[int, str, str]:
        """Spustí príkaz a vráti (exit_code, stdout, stderr)."""
        try:
            timeout_val = timeout or self.timeout
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_val,
                check=False,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Príkaz timeout po {timeout_val}s: {' '.join(cmd)}"
        except FileNotFoundError:
            return -2, "", f"Nástroj neexistuje: {cmd[0]}"

    def run_json(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Tuple[int, Dict[str, Any], str]:
        """Spustí príkaz a parsuje stdout ako JSON."""
        rc, stdout, stderr = self.run(cmd, cwd, timeout=timeout)
        if rc != 0:
            return rc, {}, stderr
        import json
        try:
            return rc, json.loads(stdout) if stdout else {}, stderr
        except json.JSONDecodeError as e:
            return -3, {}, f"JSON parse error: {e}\nOutput: {stdout[:200]}"

    def find_project_files(
        self,
        project_path: str,
        extensions: List[str],
        exclude_dirs: Optional[List[str]] = None,
    ) -> List[str]:
        """Nájde všetky súbory s danými príponami v projekte."""
        exclude = set(exclude_dirs or [".git", "__pycache__", "node_modules", "build", "dist"])
        result = []
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in exclude]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in extensions:
                    result.append(os.path.join(root, f))
        return result
