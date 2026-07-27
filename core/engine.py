import os
from typing import Any, Callable, Dict, List, Optional

from core.collector import collect_files, FileInfo
from core.config_loader import load_config
from core.finding import Finding
from core.history import HistoryManager
from core.plugin_manager import discover_plugins
from core.scheduler import run_plugins
from scoring.architecture import score_architecture
from scoring.maintainability import score_maintainability
from scoring.security import score_security


class ForensicEngine:
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_path: str = "",
        history_enabled: bool = True,
    ):
        self.config = config or load_config(config_path)
        self.project_path = ""
        self.history_enabled = history_enabled
        self.history = HistoryManager() if history_enabled else None

    def run(
        self,
        project_path: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        save_history: bool = True,
    ) -> Dict[str, Any]:
        self.project_path = os.path.abspath(project_path)

        files = collect_files(
            self.project_path,
            exclude_dirs=set(self.config.get("exclude_dirs", [])),
        )

        plugins = discover_plugins()
        plugin_results = run_plugins(plugins, self.project_path, files, progress_callback)

        all_findings: List[Finding] = []
        for plugin_name, plugin_result in plugin_results.items():
            if plugin_result.get("status") == "ok":
                data = plugin_result.get("data", {})
                if isinstance(data, list) and all(isinstance(f, Finding) for f in data):
                    all_findings.extend(data)
                    plugin_result["data"] = [f.to_dict() for f in data]

        scores = {
            "maintainability": score_maintainability(all_findings, self.config),
            "architecture": score_architecture(all_findings, self.config),
            "security": score_security(all_findings, self.config),
        }

        ai_analysis = {}
        try:
            from plugins.ai_assistant.plugin import AIAssistantPlugin
            ai = AIAssistantPlugin()
            ai_analysis = ai.classify_findings({
                "plugins": plugin_results,
                "scores": scores,
            })
        except Exception as e:
            ai_analysis = {"error": str(e)}

        result = {
            "version": "1.1.0",
            "project_path": self.project_path,
            "file_count": len(files),
            "findings": [f.to_dict() for f in all_findings],
            "plugins": plugin_results,
            "scores": scores,
            "ai_analysis": ai_analysis,
            "config": {
                k: v for k, v in self.config.items()
                if k not in ("secrets",)
            },
        }

        if self.history_enabled and save_history and self.history:
            try:
                scan_id = self.history.save_scan(result)
                result["history_id"] = scan_id
            except Exception as e:
                result["history_error"] = str(e)

        return result

    def get_history(self, project_path: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.history_enabled or not self.history:
            return []
        return self.history.get_history(project_path or self.project_path, limit=limit)

    def get_trend(self, project_path: str, metric: str = "maintainability") -> List[Dict[str, Any]]:
        if not self.history_enabled or not self.history:
            return []
        return self.history.get_trend(project_path, metric)

    def get_stats(self) -> Dict[str, Any]:
        if not self.history_enabled or not self.history:
            return {}
        return self.history.get_stats()
