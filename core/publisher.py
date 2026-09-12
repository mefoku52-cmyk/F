import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def _run(command: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


def build_and_publish(token: str) -> Dict[str, Any]:
    """
    Vytvorí Python distribúciu a odošle ju na PyPI cez Twine.

    Token sa nepridáva do výstupu ani do príkazových logov.
    """
    result: Dict[str, Any] = {
        "status": "ok",
        "output": "",
        "errors": "",
    }

    if not token or not token.strip():
        result["status"] = "error"
        result["errors"] = "PyPI token nie je zadaný."
        return result

    project_root = Path.cwd()
    dist_dir = project_root / "dist"

    try:
        install_proc = _run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "build",
                "twine",
            ]
        )

        if install_proc.returncode != 0:
            result["status"] = "error"
            result["errors"] = (
                "Nepodarilo sa nainštalovať build a twine.\n"
                f"{install_proc.stderr}"
            )
            return result

        result["output"] += install_proc.stdout

        build_proc = _run([sys.executable, "-m", "build"])

        if build_proc.returncode != 0:
            result["status"] = "error"
            result["errors"] = (
                "Vytvorenie distribučného balíka zlyhalo.\n"
                f"{build_proc.stderr}"
            )
            return result

        result["output"] += build_proc.stdout

        packages = sorted(
            str(path)
            for path in dist_dir.iterdir()
            if path.is_file() and path.suffix in {".whl", ".gz"}
        )

        if not packages:
            result["status"] = "error"
            result["errors"] = "Po builde sa v priečinku dist nenašiel žiadny balík."
            return result

        check_proc = _run(
            [sys.executable, "-m", "twine", "check", *packages]
        )

        if check_proc.returncode != 0:
            result["status"] = "error"
            result["errors"] = (
                "Kontrola balíka cez twine check zlyhala.\n"
                f"{check_proc.stderr}"
            )
            return result

        result["output"] += check_proc.stdout

        upload_proc = _run(
            [
                sys.executable,
                "-m",
                "twine",
                "upload",
                "--non-interactive",
                "--username",
                "__token__",
                "--password",
                token.strip(),
                *packages,
            ]
        )

        if upload_proc.returncode != 0:
            result["status"] = "error"
            result["errors"] = (
                "Nahranie balíka na PyPI zlyhalo.\n"
                f"{upload_proc.stderr}"
            )
            return result

        result["output"] += upload_proc.stdout
        return result

    except FileNotFoundError as exc:
        result["status"] = "error"
        result["errors"] = f"Nenašiel sa potrebný program: {exc}"
        return result
    except Exception as exc:
        result["status"] = "error"
        result["errors"] = f"Neočakávaná chyba pri publikovaní: {exc}"
        return result
