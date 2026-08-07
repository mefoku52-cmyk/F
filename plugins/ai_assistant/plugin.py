"""
AI Asistent plugin – lokálny filter false positives.
Nepotrebuje externé API. Používa heuristiky a pattern matching.
"""

from typing import Any, Dict, List

from core.collector import FileInfo
from core.plugin_manager import Plugin


class AIAssistantPlugin(Plugin):
    @property
    def name(self) -> str:
        return "ai_assistant"

    def supports(self, project_path: str, files: List[FileInfo]) -> bool:
        # Beží vždy, lebo analyzuje výstupy ostatných pluginov
        return True

    def analyze(self, project_path: str, files: List[FileInfo]) -> Dict[str, Any]:
        # Tento plugin neanalyzuje súbory priamo – beží ako post-processor
        # Reálna logika je v metóde classify_findings, ktorú volá engine
        return {
            "status": "post_processor",
            "description": "Analyzuje nálezy ostatných pluginov a klasifikuje ich pravdepodobnosť",
        }

    @staticmethod
    def classify_findings(raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-processing: prejde všetky nálezy a pridá confidence score.
        Volané z engine.py po skončení všetkých pluginov.
        """
        classifications = []

        # --- Python dead code ---
        python_data = raw_result.get("plugins", {}).get("python", {}).get("data", {})
        for candidate in python_data.get("dead_code_candidates", []):
            func = candidate.get("function", "")
            path = candidate.get("path", "")

            # Heuristiky pre FP
            fp_score = 0.0
            reasons = []

            if "server" in path and func.startswith("do_"):
                fp_score += 0.95
                reasons.append("HTTP handler override")
            if func in ("log_message", "setup", "handle", "finish_request"):
                fp_score += 0.90
                reasons.append("Framework lifecycle method")
            if "sdk" in path and any(k in func for k in ["scan", "report", "client"]):
                fp_score += 0.85
                reasons.append("Public SDK API")
            if func.startswith("__") and func.endswith("__"):
                fp_score += 0.99
                reasons.append("Dunder method")

            confidence = 1.0 - fp_score
            classifications.append(
                {
                    "plugin": "python",
                    "type": "dead_code",
                    "file": path,
                    "function": func,
                    "confidence": round(confidence, 2),
                    "is_likely_real": confidence > 0.5,
                    "reasons": reasons if reasons else ["No obvious FP indicators"],
                }
            )

        # --- Shell findings ---
        shell_data = raw_result.get("plugins", {}).get("shell", {}).get("data", {})
        for finding in shell_data.get("findings", []):
            ftype = finding.get("type", "")
            line = finding.get("content", "")

            fp_score = 0.0
            reasons = []

            if ftype == "hardcoded_path" and "#!" in line:
                fp_score += 0.95
                reasons.append("Shebang line")
            if ftype == "sudo" and ('"' in line or "'" in line):
                fp_score += 0.90
                reasons.append("Inside string literal")
            if 'r"' in line or "r'" in line:
                fp_score += 0.80
                reasons.append("Inside regex pattern")

            confidence = 1.0 - fp_score
            classifications.append(
                {
                    "plugin": "shell",
                    "type": ftype,
                    "file": finding.get("file"),
                    "line": finding.get("line"),
                    "confidence": round(confidence, 2),
                    "is_likely_real": confidence > 0.5,
                    "reasons": reasons if reasons else ["No obvious FP indicators"],
                }
            )

        # Agregácia
        real_count = sum(1 for c in classifications if c["is_likely_real"])
        fp_count = len(classifications) - real_count

        return {
            "total_findings": len(classifications),
            "likely_real": real_count,
            "likely_false_positive": fp_count,
            "classifications": classifications,
            "recommendation": f"Z {len(classifications)} nálezov je pravdepodobne {fp_count} false positive. Odporúčam ručnú kontrolu {real_count} zvyšných.",
        }
