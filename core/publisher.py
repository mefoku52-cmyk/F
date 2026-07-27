import os
import subprocess
import sys
from typing import Dict, Any

def build_and_publish(token: str) -> Dict[str, Any]:
    """
    Vygeneruje balík a odošle na PyPI pomocou twine.
    Vyžaduje nainštalované build a twine.
    """
    result = {"status": "ok", "output": "", "errors": ""}
    try:
        # Inštalácia potrebných nástrojov
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "build", "twine"], 
                       capture_output=True, check=False)
        # Build
        build_proc = subprocess.run([sys.executable, "-m", "build"], 
                                    capture_output=True, text=True, check=False)
        if build_proc.returncode != 0:
            result["status"] = "error"
            result["errors"] = build_proc.stderr
            return result
        result["output"] += build_proc.stdout
        # Upload
        upload_proc = subprocess.run(
            [sys.executable, "-m", "twine", "upload", "--username", "__token__", "--password", token, "dist/*"],
            capture_output=True, text=True, check=False
        )
        if upload_proc.returncode != 0:
            result["status"] = "error"
            result["errors"] = upload_proc.stderr
            return result
        result["output"] += upload_proc.stdout
        return result
    except Exception as e:
        return {"status": "error", "errors": str(e)}
