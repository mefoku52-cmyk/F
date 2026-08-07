import json
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict

_SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)

from core.engine import ForensicEngine
from core.fixer import (
    fix_duplicates,
    get_deadcode_suggestions,
    get_dangerous_suggestions,
)
from core.history import HistoryManager
from core.publisher import build_and_publish
from reports import json_report, markdown_report, html_report

_lock = threading.Lock()
_last_result = None


def _scan_project(path: str, formats: list) -> Dict[str, Any]:
            global _last_result
    engine = ForensicEngine(history_enabled=True)
    result = engine.run(path)
    _last_result = result
    output_dir = os.path.join(path, "forensicsuite_report")
    os.makedirs(output_dir, exist_ok=True)
    for fmt in formats:
        if fmt == "json":
            json_report.generate(result, os.path.join(output_dir, "report.json"))
        elif fmt == "markdown":
            markdown_report.generate(result, os.path.join(output_dir, "report.md"))
        elif fmt == "html":
            html_report.generate(result, os.path.join(output_dir, "report.html"))
    return result


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok"})
        elif self.path == "/version":
            from version import __version__

            self._send_json({"version": __version__})
        elif self.path == "/last_report":
                    global _last_result
            if _last_result:
                self._send_json(_last_result)
            else:
                self._send_json({"error": "Žiadny predošlý sken"}, 404)
        elif self.path == "/history":
            history = HistoryManager()
            data = history.get_all_history(limit=100)
            self._send_json({"status": "ok", "history": data})
        elif self.path == "/stats":
            history = HistoryManager()
            stats = history.get_stats()
            self._send_json({"status": "ok", "stats": stats})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
                global _last_result
        if self.path == "/scan":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
                return
            path = payload.get("path", ".")
            formats = payload.get("formats", ["json"])
            with _lock:
                try:
                    result = _scan_project(path, formats)
                    self._send_json({"status": "ok", "result": result})
                except Exception as e:
                    self._send_json({"status": "error", "error": str(e)}, 500)

        elif self.path == "/fix/duplicates":
            if not _last_result:
                self._send_json({"error": "Žiadny predošlý sken"}, 400)
                return
            # Získame findings z filesystem pluginu
            fs_plugin = _last_result.get("plugins", {}).get("filesystem", {})
            if fs_plugin.get("status") == "ok":
                data = fs_plugin.get("data", [])
                if isinstance(data, list):
                    # Hľadáme Finding s duplicitami
                    duplicates = []
                    for f in data:
                        if f.get("message", "").startswith("Duplicitné súbory"):
                            duplicates.append(
                                f.get("metadata", {}).get("duplicate_group", [])
                            )
                    # Ak sme nenašli v metadata, skúsime alternatívny spôsob
                    if not duplicates:
                        # Starší formát: priamo v data
                        fs_data = (
                            _last_result.get("plugins", {})
                            .get("filesystem", {})
                            .get("data", {})
                        )
                        if isinstance(fs_data, dict):
                            duplicates = fs_data.get("duplicate_groups", [])
                else:
                    duplicates = data.get("duplicate_groups", [])
            else:
                duplicates = []
            if not duplicates:
                self._send_json(
                    {"status": "ok", "message": "Žiadne duplicity", "removed": []}
                )
                return
            project_path = _last_result.get("project_path", ".")
            result = fix_duplicates(project_path, duplicates)
            self._send_json({"status": "ok", "result": result})

        elif self.path == "/fix/deadcode":
            if not _last_result:
                self._send_json({"error": "Žiadny predošlý sken"}, 400)
                return
            python_data = (
                _last_result.get("plugins", {}).get("python", {}).get("data", {})
            )
            deadcode = python_data.get("dead_code_candidates", [])
            suggestions = get_deadcode_suggestions(deadcode)
            self._send_json({"status": "ok", "suggestions": suggestions})

        elif self.path == "/fix/dangerous":
            if not _last_result:
                self._send_json({"error": "Žiadny predošlý sken"}, 400)
                return
            shell_data = (
                _last_result.get("plugins", {}).get("shell", {}).get("data", {})
            )
            dangerous = shell_data.get("findings", [])
            suggestions = get_dangerous_suggestions(dangerous)
            self._send_json({"status": "ok", "suggestions": suggestions})

        elif self.path == "/publish/pypi":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                token = payload.get("token", "")
            except:
                self._send_json({"error": "Invalid JSON"}, 400)
                return
            if not token:
                self._send_json({"error": "Token je povinný"}, 400)
                return
            result = build_and_publish(token)
            self._send_json(result)

        elif self.path == "/export/pdf":
            if not _last_result:
                self._send_json({"error": "Žiadny predošlý sken"}, 400)
                return
            project_path = _last_result.get("project_path", ".")
            output_dir = os.path.join(project_path, "forensicsuite_report")
            os.makedirs(output_dir, exist_ok=True)
            html_report.generate(
                _last_result, os.path.join(output_dir, "report.pdf.html")
            )
            self._send_json(
                {
                    "status": "ok",
                    "message": "PDF export pripravený",
                    "path": os.path.join(output_dir, "report.pdf.html"),
                }
            )

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run_server(host: str = "0.0.0.0",, port: int = 8765) -> None:
            global _last_result
    # Automatický sken pri štarte – spustíme v samostatnom vlákne
    import threading

    def auto_scan():
        try:
            print("🔄 Spúšťam automatický sken na pozadí...")
            _scan_project(".", ["json"])
            print("✅ Automatický sken dokončený")
        except Exception as e:
            print(f"⚠️ Automatický sken zlyhal: {e}")

    threading.Thread(target=auto_scan, daemon=True).start()
    server = HTTPServer((host, port), _Handler)
    print(f"ForensicSuite API beží na http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer ukončený.")
        server.shutdown()
