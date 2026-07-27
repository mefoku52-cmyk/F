import logging
import time
from typing import Any, Dict, List, Callable, Optional

from core.collector import FileInfo
from core.plugin_manager import Plugin

logger = logging.getLogger("forensicsuite.scheduler")


def run_plugins(
    plugins: List[Plugin],
    project_path: str,
    files: List[FileInfo],
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    total = len(plugins)
    for idx, plugin in enumerate(plugins):
        if progress_callback:
            progress_callback(plugin.name, idx + 1, total)
        start = time.monotonic()
        try:
            if not plugin.supports(project_path, files):
                results[plugin.name] = {
                    "status": "skipped",
                    "reason": "plugin nepodporuje tento projekt",
                    "elapsed_seconds": 0.0,
                    "data": {},
                }
                continue
            data = plugin.analyze(project_path, files)
            elapsed = time.monotonic() - start
            results[plugin.name] = {
                "status": "ok",
                "elapsed_seconds": round(elapsed, 3),
                "data": data,
            }
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.exception("Plugin '%s' zlyhal", plugin.name)
            results[plugin.name] = {
                "status": "error",
                "elapsed_seconds": round(elapsed, 3),
                "error": str(e),
            }
    return results

