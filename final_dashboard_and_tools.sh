#!/usr/bin/env bash
set -euo pipefail

echo "=============================================================="
echo "   FORENSICSUITE – KOMPLETNÝ DASHBOARD + NÁSTROJE"
echo "=============================================================="

# 1. Rozšírenie core/history.py o metódu get_all_history
cat > core/history.py << 'HISTORY_EOF'
import json
import os
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class HistoryManager:
    def __init__(self, db_path: str = "forensicsuite_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                project_path TEXT NOT NULL,
                file_count INTEGER,
                scores_json TEXT,
                findings_json TEXT,
                plugins_json TEXT,
                version TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_path ON scans(project_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON scans(timestamp)")
        conn.commit()
        conn.close()

    def save_scan(self, result: Dict[str, Any]) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scans (
                timestamp, project_path, file_count,
                scores_json, findings_json, plugins_json, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            int(time.time()),
            result.get("project_path", ""),
            result.get("file_count", 0),
            json.dumps(result.get("scores", {})),
            json.dumps(result.get("findings", [])),
            json.dumps(result.get("plugins", {})),
            result.get("version", ""),
        ))
        scan_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return scan_id

    def get_history(self, project_path: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM scans"
        params = []
        if project_path:
            query += " WHERE project_path = ?"
            params.append(project_path)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            data = dict(row)
            data["scores"] = json.loads(data.get("scores_json", "{}"))
            data["findings"] = json.loads(data.get("findings_json", "[]"))
            data["plugins"] = json.loads(data.get("plugins_json", "{}"))
            data["datetime"] = datetime.fromtimestamp(data["timestamp"]).isoformat()
            data.pop("scores_json", None); data.pop("findings_json", None); data.pop("plugins_json", None)
            result.append(data)
        return result

    def get_all_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.get_history(None, limit)

    def get_stats(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scans")
        total_scans = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT project_path) FROM scans")
        total_projects = cursor.fetchone()[0]
        cursor.execute("SELECT project_path, COUNT(*) as count FROM scans GROUP BY project_path ORDER BY count DESC LIMIT 5")
        top_projects = [{"project": row[0], "scans": row[1]} for row in cursor.fetchall()]
        conn.close()
        return {"total_scans": total_scans, "total_projects": total_projects, "top_projects": top_projects}
HISTORY_EOF
echo "[OK] core/history.py – pridaná get_all_history"

# 2. Vytvorenie core/publisher.py pre PyPI
cat > core/publisher.py << 'PUBLISHER_EOF'
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
PUBLISHER_EOF
echo "[OK] core/publisher.py"

# 3. Rozšírenie server/api.py o nové endpointy
cat > server/api.py << 'API_EOF'
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
from core.fixer import fix_duplicates, get_deadcode_suggestions, get_dangerous_suggestions
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
            fs_data = _last_result.get("plugins", {}).get("filesystem", {}).get("data", {})
            duplicates = fs_data.get("duplicate_groups", [])
            if not duplicates:
                self._send_json({"status": "ok", "message": "Žiadne duplicity", "removed": []})
                return
            project_path = _last_result.get("project_path", ".")
            result = fix_duplicates(project_path, duplicates)
            self._send_json({"status": "ok", "result": result})

        elif self.path == "/fix/deadcode":
            if not _last_result:
                self._send_json({"error": "Žiadny predošlý sken"}, 400)
                return
            python_data = _last_result.get("plugins", {}).get("python", {}).get("data", {})
            deadcode = python_data.get("dead_code_candidates", [])
            suggestions = get_deadcode_suggestions(deadcode)
            self._send_json({"status": "ok", "suggestions": suggestions})

        elif self.path == "/fix/dangerous":
            if not _last_result:
                self._send_json({"error": "Žiadny predošlý sken"}, 400)
                return
            shell_data = _last_result.get("plugins", {}).get("shell", {}).get("data", {})
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
            # Jednoduchý PDF export – uložíme HTML ako PDF cez wkhtmltopdf (ak je dostupný)
            # Zjednodušene: vygenerujeme HTML a uložíme ako .html.pdf
            project_path = _last_result.get("project_path", ".")
            output_dir = os.path.join(project_path, "forensicsuite_report")
            os.makedirs(output_dir, exist_ok=True)
            html_report.generate(_last_result, os.path.join(output_dir, "report.pdf.html"))
            self._send_json({"status": "ok", "message": "PDF export pripravený", "path": os.path.join(output_dir, "report.pdf.html")})

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def run_server(host: str = "0.0.0.0", port: int = 8765) -> None:
    server = HTTPServer((host, port), _Handler)
    print(f"ForensicSuite API beží na http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer ukončený.")
        server.shutdown()
API_EOF
echo "[OK] server/api.py – rozšírené o /history, /stats, /publish/pypi, /export/pdf"

# 4. Vytvorenie nového dashboard/index.html
cat > dashboard/index.html << 'DASH_EOF'
<!DOCTYPE html>
<html lang="sk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ForensicSuite Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', Roboto, system-ui, sans-serif;
    background: #0a0f1a;
    color: #e2e8f0;
    min-height: 100vh;
    position: relative;
    overflow-x: hidden;
  }
  /* Pozadie – ozubené kolesá */
  body::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
      radial-gradient(circle at 10% 20%, rgba(96,165,250,0.03) 0%, transparent 50%),
      radial-gradient(circle at 90% 80%, rgba(96,165,250,0.03) 0%, transparent 50%),
      repeating-conic-gradient(from 0deg at 50% 50%, transparent 0deg 10deg, rgba(96,165,250,0.01) 10deg 20deg);
    pointer-events: none;
    z-index: 0;
  }
  /* Ozubené kolesá SVG pozadie */
  .gears-bg {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    z-index: 0;
    opacity: 0.04;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 800'%3E%3Cpath d='M400 100 L420 160 L490 130 L480 200 L550 190 L520 260 L590 270 L540 330 L600 360 L530 400 L600 440 L540 470 L590 530 L520 540 L550 610 L480 600 L490 670 L420 640 L400 700 L380 640 L310 670 L320 600 L250 610 L280 540 L210 530 L260 470 L200 440 L270 400 L200 360 L260 330 L210 270 L280 260 L250 190 L320 200 L310 130 L380 160 L400 100Z' fill='%2360a5fa'/%3E%3C/svg%3E");
    background-size: 600px 600px;
    background-position: 80% 20%;
    background-repeat: no-repeat;
  }
  .container {
    position: relative;
    z-index: 1;
    max-width: 1300px;
    margin: 0 auto;
    padding: 20px;
  }
  header { text-align: center; padding: 30px 0 20px; border-bottom: 1px solid #1e293b; margin-bottom: 25px; }
  header h1 { font-size: 2.4em; color: #60a5fa; font-weight: 700; letter-spacing: -0.5px; }
  header h1 span { color: #e2e8f0; }
  header p { color: #94a3b8; margin-top: 6px; font-size: 0.95em; }
  .toolbar {
    display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;
    margin-bottom: 25px; padding: 12px 16px;
    background: rgba(30, 41, 59, 0.7);
    backdrop-filter: blur(8px);
    border-radius: 12px;
    border: 1px solid #1e293b;
  }
  .toolbar .group { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; padding: 0 6px; border-right: 1px solid #1e293b; }
  .toolbar .group:last-child { border-right: none; }
  .toolbar .group-label { font-size: 0.7em; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-right: 4px; }
  .toolbar button {
    background: #1e293b; color: #e2e8f0; border: none;
    padding: 6px 14px; border-radius: 6px; cursor: pointer;
    font-size: 13px; transition: all 0.2s; white-space: nowrap;
  }
  .toolbar button:hover { background: #334155; transform: translateY(-1px); }
  .toolbar button.primary { background: #2563eb; }
  .toolbar button.primary:hover { background: #1d4ed8; }
  .toolbar button.success { background: #16a34a; }
  .toolbar button.success:hover { background: #15803d; }
  .toolbar button.danger { background: #dc2626; }
  .toolbar button.danger:hover { background: #b91c1c; }
  .toolbar button.warning { background: #d97706; }
  .toolbar button.warning:hover { background: #b45309; }
  .toolbar button.info { background: #0891b2; }
  .toolbar button.info:hover { background: #0e7490; }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 25px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px; }
  .card {
    background: rgba(30, 41, 59, 0.85);
    backdrop-filter: blur(4px);
    border-radius: 14px; padding: 22px 24px;
    border: 1px solid #1e293b;
    transition: all 0.2s;
  }
  .card:hover { border-color: #334155; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
  .card h3 { color: #94a3b8; font-size: 0.75em; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 10px; }
  .score-value { font-size: 2.8em; font-weight: 700; }
  .score-value.good { color: #4ade80; }
  .score-value.warn { color: #fbbf24; }
  .score-value.bad { color: #f87171; }
  .score-value.na { color: #64748b; }
  .chart-container { height: 200px; margin-top: 8px; }
  .detail-section {
    margin-top: 20px;
    border-top: 1px solid #1e293b;
    padding-top: 16px;
  }
  .detail-section summary {
    cursor: pointer; color: #60a5fa; font-weight: 600;
    padding: 8px 0; font-size: 1.05em;
    list-style: none; display: flex; align-items: center; gap: 10px;
  }
  .detail-section summary::-webkit-details-marker { display: none; }
  .detail-section summary::before {
    content: '▶'; font-size: 0.8em; transition: transform 0.2s;
    color: #60a5fa;
  }
  .detail-section[open] summary::before { transform: rotate(90deg); }
  .detail-section .content {
    padding: 12px 0 6px;
    max-height: 400px; overflow-y: auto;
  }
  .finding-item { padding: 6px 10px; border-bottom: 1px solid #1e293b; font-size: 13px; }
  .finding-item .sev { font-weight: 600; }
  .finding-item .sev.CRITICAL { color: #f87171; }
  .finding-item .sev.HIGH { color: #fb923c; }
  .finding-item .sev.MEDIUM { color: #fbbf24; }
  .finding-item .sev.LOW { color: #4ade80; }
  .finding-item .sev.INFO { color: #94a3b8; }
  .toast {
    position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
    background: #1e293b; border: 1px solid #334155;
    padding: 14px 28px; border-radius: 10px; color: #e2e8f0;
    z-index: 999; display: none; font-size: 14px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
    max-width: 90%; text-align: center;
  }
  .toast.show { display: block; }
  .toast.success { border-color: #16a34a; }
  .toast.error { border-color: #dc2626; }
  .footer { text-align: center; padding: 30px; color: #475569; font-size: 0.85em; border-top: 1px solid #1e293b; margin-top: 25px; }
  .loading { text-align: center; padding: 60px 20px; color: #94a3b8; }
  #dropzone {
    border: 2px dashed #1e293b; border-radius: 12px;
    padding: 25px; text-align: center; margin-bottom: 20px;
    cursor: pointer; transition: border-color 0.3s;
    background: rgba(30,41,59,0.3);
  }
  #dropzone:hover { border-color: #60a5fa; }
  #dropzone p { color: #94a3b8; }
  @media (max-width: 768px) {
    .grid-2, .grid-3 { grid-template-columns: 1fr; }
    .toolbar .group { border-right: none; border-bottom: 1px solid #1e293b; padding-bottom: 6px; }
  }
  .gears-bg { display: block; }
</style>
</head>
<body>
<div class="gears-bg"></div>
<div class="container">
  <header>
    <h1>🔍 ForensicSuite <span>Dashboard</span></h1>
    <p>v1.1.0 – profesionálna analýza kvality kódu</p>
  </header>

  <!-- Toolbar -->
  <div class="toolbar" id="toolbar">
    <div class="group">
      <span class="group-label">🔧</span>
      <button class="primary" id="btnScan">🔄 Spustiť sken</button>
      <button class="info" id="btnHistory">📊 História</button>
    </div>
    <div class="group">
      <span class="group-label">🛠️</span>
      <button class="success" id="btnFixDuplicates">📦 Odstrániť duplicity</button>
      <button class="warning" id="btnShowDeadCode">💀 Dead code</button>
      <button class="warning" id="btnShowDangerous">⚠️ Nebezpečné príkazy</button>
    </div>
    <div class="group">
      <span class="group-label">📤</span>
      <button class="info" id="btnExportPDF">📄 Export PDF</button>
      <button class="primary" id="btnPublishPyPI">📦 Publikovať na PyPI</button>
    </div>
    <div class="group">
      <span class="group-label">🗑️</span>
      <button class="danger" id="btnReset">Reset</button>
    </div>
  </div>

  <div id="dropzone">
    <p>📁 Klikni sem a vyber <code>report.json</code></p>
    <input type="file" id="fileInput" accept=".json" style="display:none">
  </div>

  <div id="loading" class="loading">⏳ Načítavam...</div>

  <div id="content" style="display:none">
    <div id="scores-grid" class="grid-3"></div>
    <div class="grid-2">
      <div class="card"><h3>📊 Radar skóre</h3><div class="chart-container"><canvas id="radarChart"></canvas></div></div>
      <div class="card"><h3>📈 Trend (z histórie)</h3><div class="chart-container"><canvas id="trendChart"></canvas></div></div>
    </div>
    <div class="card">
      <h3>📋 Nálezy podľa severity</h3>
      <div class="chart-container" style="height:150px"><canvas id="severityChart"></canvas></div>
    </div>

    <!-- Detail sekcie (rozbaľovacie) -->
    <div class="detail-section" id="detailFindings">
      <summary>🔎 Detail nálezov</summary>
      <div class="content" id="findingsList"></div>
    </div>
    <div class="detail-section" id="detailCVE">
      <summary>🛡️ CVE zraniteľnosti</summary>
      <div class="content" id="cveList"></div>
    </div>
    <div class="detail-section" id="detailHistory">
      <summary>📊 História skenov</summary>
      <div class="content" id="historyList"></div>
    </div>
  </div>

  <div id="error" style="display:none; color:#f87171; text-align:center; padding:40px;">
    ❌ Nepodarilo sa načítať report.json.
  </div>

  <div class="footer">ForensicSuite v1.1.0 – generované lokálne v Termuxe</div>
</div>

<!-- Toast -->
<div id="toast" class="toast"></div>

<script>
// --- Elementy ---
const loadingEl = document.getElementById('loading');
const contentEl = document.getElementById('content');
const errorEl = document.getElementById('error');
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const toastEl = document.getElementById('toast');

let radarChartInstance = null, trendChartInstance = null, severityChartInstance = null;
let currentData = null, toastTimeout = null;
const API_BASE = 'http://localhost:8765';

// --- Toast ---
function showToast(msg, duration = 3000, type = '') {
  toastEl.textContent = msg;
  toastEl.className = 'toast show ' + type;
  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => { toastEl.classList.remove('show'); }, duration);
}

// --- API volania ---
async function callApi(endpoint, method = 'GET', data = null) {
  try {
    const options = { method, headers: { 'Content-Type': 'application/json' } };
    if (data) options.body = JSON.stringify(data);
    const response = await fetch(API_BASE + endpoint, options);
    const result = await response.json();
    return result;
  } catch (err) {
    showToast('❌ Chyba API: ' + err.message, 4000, 'error');
    return null;
  }
}

// --- Načítanie report.json ---
async function loadReport() {
  try {
    const response = await fetch('report.json?t=' + Date.now());
    if (!response.ok) throw new Error('Súbor neexistuje');
    const data = await response.json();
    currentData = data;
    render(data);
    loadingEl.style.display = 'none';
    contentEl.style.display = 'block';
    dropzone.style.display = 'none';
    errorEl.style.display = 'none';
    // Načítať históriu pre trend
    loadHistory();
  } catch (err) {
    loadingEl.style.display = 'none';
    dropzone.style.display = 'block';
    errorEl.style.display = 'block';
  }
}

// --- Načítanie histórie ---
async function loadHistory() {
  const result = await callApi('/history');
  if (result && result.status === 'ok' && result.history && result.history.length > 0) {
    renderTrendFromHistory(result.history);
    renderHistoryList(result.history);
  }
}

// --- Renderovanie ---
function render(data) {
  // Skóre
  const scoresGrid = document.getElementById('scores-grid');
  scoresGrid.innerHTML = '';
  const scoreMap = {
    'maintainability': '🛠️ Udržateľnosť',
    'architecture': '🏗️ Architektúra',
    'security': '🔒 Bezpečnosť'
  };
  for (const [key, label] of Object.entries(scoreMap)) {
    const sdata = data.scores && data.scores[key] ? data.scores[key] : { score: null };
    const score = sdata.score;
    let cls = 'score-value na', display = 'N/A';
    if (score !== null && score !== undefined) {
      display = score;
      if (score >= 80) cls = 'score-value good';
      else if (score >= 50) cls = 'score-value warn';
      else cls = 'score-value bad';
    }
    scoresGrid.innerHTML += `
      <div class="card">
        <h3>${label}</h3>
        <div class="${cls}">${display}</div>
        ${score !== null && score !== undefined ? '<div style="font-size:12px;color:#94a3b8;">/ 100</div>' : ''}
      </div>
    `;
  }

  // Radar
  const radarCtx = document.getElementById('radarChart').getContext('2d');
  if (radarChartInstance) radarChartInstance.destroy();
  const radarData = [], radarLabels = [];
  for (const [key, label] of Object.entries(scoreMap)) {
    const sdata = data.scores && data.scores[key] ? data.scores[key] : { score: null };
    const score = sdata.score;
    if (score !== null && score !== undefined) { radarData.push(score); radarLabels.push(label); }
  }
  radarChartInstance = new Chart(radarCtx, {
    type: 'radar',
    data: { labels: radarLabels, datasets: [{ label: 'Skóre', data: radarData, backgroundColor: 'rgba(96,165,250,0.2)', borderColor: 'rgba(96,165,250,1)', pointBackgroundColor: 'rgba(96,165,250,1)', fill: true }] },
    options: { responsive: true, maintainAspectRatio: false, scales: { r: { min: 0, max: 100, ticks: { stepSize: 20, color: '#94a3b8' }, grid: { color: '#334155' } } }, plugins: { legend: { labels: { color: '#e2e8f0' } } } }
  });

  // Severity graf
  const sevCtx = document.getElementById('severityChart').getContext('2d');
  if (severityChartInstance) severityChartInstance.destroy();
  const findings = data.findings || [];
  const sevCount = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
  findings.forEach(f => { const sev = f.severity || 'INFO'; if (sevCount[sev] !== undefined) sevCount[sev]++; });
  const sevLabels = Object.keys(sevCount), sevData = Object.values(sevCount);
  const sevColors = ['#f87171','#fb923c','#fbbf24','#4ade80','#94a3b8'];
  severityChartInstance = new Chart(sevCtx, {
    type: 'bar',
    data: { labels: sevLabels, datasets: [{ label: 'Počet nálezov', data: sevData, backgroundColor: sevColors, borderRadius: 4 }] },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, ticks: { stepSize: 1, color: '#94a3b8' }, grid: { color: '#334155' } }, x: { ticks: { color: '#94a3b8' }, grid: { display: false } } }, plugins: { legend: { display: false } } }
  });

  // Zoznam nálezov
  const listDiv = document.getElementById('findingsList');
  listDiv.innerHTML = '';
  if (findings.length === 0) {
    listDiv.innerHTML = '<div class="finding-item" style="color:#4ade80;">✅ Žiadne nálezy</div>';
  } else {
    findings.slice(0, 100).forEach(f => {
      const sev = f.severity || 'INFO';
      const msg = f.message || 'Bez správy';
      const loc = f.location || '';
      listDiv.innerHTML += `<div class="finding-item"><span class="sev ${sev}">[${sev}]</span> ${msg} ${loc ? '<span style="color:#64748b;font-size:12px;"> – '+loc+'</span>' : ''}</div>`;
    });
    if (findings.length > 100) {
      listDiv.innerHTML += '<div class="finding-item" style="color:#64748b;">... a ďalších '+(findings.length-100)+' nálezov</div>';
    }
  }

  // CVE zoznam
  const cveList = document.getElementById('cveList');
  cveList.innerHTML = '';
  const cves = findings.filter(f => f.severity === 'CRITICAL' && f.message.includes('CVE'));
  if (cves.length === 0) {
    cveList.innerHTML = '<div class="finding-item" style="color:#4ade80;">✅ Žiadne CVE</div>';
  } else {
    cves.forEach(c => {
      cveList.innerHTML += `<div class="finding-item"><span class="sev CRITICAL">[CRITICAL]</span> ${c.message}</div>`;
    });
  }
}

// --- Render trendu z histórie ---
function renderTrendFromHistory(history) {
  if (!history || history.length < 1) return;
  const trendCtx = document.getElementById('trendChart').getContext('2d');
  if (trendChartInstance) trendChartInstance.destroy();
  // Zoradiť podľa času
  const sorted = history.sort((a,b) => a.timestamp - b.timestamp);
  const labels = sorted.map(h => h.datetime ? h.datetime.slice(5,16) : '');
  const scores = sorted.map(h => h.scores?.maintainability?.score ?? 0);
  trendChartInstance = new Chart(trendCtx, {
    type: 'line',
    data: { labels, datasets: [{ label: 'Maintainability', data: scores, borderColor: '#4ade80', backgroundColor: 'rgba(74,222,128,0.1)', fill: true, tension: 0.3 }] },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 100, ticks: { color: '#94a3b8' }, grid: { color: '#334155' } }, x: { ticks: { color: '#94a3b8', maxTicksLimit: 10, grid: { color: '#334155' } } } }, plugins: { legend: { labels: { color: '#e2e8f0' } } } }
  });
}

function renderHistoryList(history) {
  const list = document.getElementById('historyList');
  list.innerHTML = '';
  if (!history || history.length === 0) {
    list.innerHTML = '<div class="finding-item">Žiadna história</div>';
    return;
  }
  history.slice(0, 20).forEach(h => {
    const date = h.datetime || 'N/A';
    const maint = h.scores?.maintainability?.score ?? 'N/A';
    const arch = h.scores?.architecture?.score ?? 'N/A';
    const sec = h.scores?.security?.score ?? 'N/A';
    list.innerHTML += `<div class="finding-item">📅 ${date} | 🛠️ ${maint} | 🏗️ ${arch} | 🔒 ${sec}</div>`;
  });
  if (history.length > 20) {
    list.innerHTML += `<div class="finding-item" style="color:#64748b;">... a ďalších ${history.length-20} záznamov</div>`;
  }
}

// --- Tlačidlá ---
document.getElementById('btnScan').addEventListener('click', async () => {
  showToast('⏳ Spúšťam sken...', 5000);
  const result = await callApi('/scan', 'POST', { path: '.', formats: ['json'] });
  if (result && result.status === 'ok') {
    showToast('✅ Sken dokončený!', 3000, 'success');
    setTimeout(loadReport, 1000);
  } else {
    showToast('❌ Sken zlyhal: ' + (result?.error || 'neznáma chyba'), 4000, 'error');
  }
});

document.getElementById('btnFixDuplicates').addEventListener('click', async () => {
  showToast('⏳ Odstraňujem duplicity...', 5000);
  const result = await callApi('/fix/duplicates', 'POST');
  if (result && result.status === 'ok') {
    if (result.result && result.result.removed && result.result.removed.length > 0) {
      showToast('✅ Odstránené duplicity: ' + result.result.removed.join(', '), 5000, 'success');
    } else {
      showToast('✅ Žiadne duplicity', 3000, 'success');
    }
    setTimeout(loadReport, 1000);
  } else {
    showToast('❌ Chyba: ' + (result?.error || 'neznáma chyba'), 4000, 'error');
  }
});

document.getElementById('btnShowDeadCode').addEventListener('click', async () => {
  const result = await callApi('/fix/deadcode', 'POST');
  if (result && result.status === 'ok') {
    if (result.suggestions && result.suggestions.length > 0) {
      const list = result.suggestions.map(s => `${s.function} (${s.path}:${s.lineno})`).join('\n');
      alert('💀 Dead code:\n\n' + list);
    } else { alert('💀 Žiadny dead code.'); }
  } else { showToast('❌ Chyba: ' + (result?.error || 'neznáma chyba'), 4000, 'error'); }
});

document.getElementById('btnShowDangerous').addEventListener('click', async () => {
  const result = await callApi('/fix/dangerous', 'POST');
  if (result && result.status === 'ok') {
    if (result.suggestions && result.suggestions.length > 0) {
      const list = result.suggestions.map(s => `[${s.type}] ${s.content} (${s.file}:${s.line})`).join('\n');
      alert('⚠️ Nebezpečné príkazy:\n\n' + list);
    } else { alert('⚠️ Žiadne nebezpečné príkazy.'); }
  } else { showToast('❌ Chyba: ' + (result?.error || 'neznáma chyba'), 4000, 'error'); }
});

document.getElementById('btnExportPDF').addEventListener('click', async () => {
  showToast('⏳ Generujem PDF...', 3000);
  const result = await callApi('/export/pdf', 'POST');
  if (result && result.status === 'ok') {
    showToast('✅ PDF pripravený: ' + result.path, 5000, 'success');
  } else {
    showToast('❌ Chyba: ' + (result?.error || 'neznáma chyba'), 4000, 'error');
  }
});

document.getElementById('btnPublishPyPI').addEventListener('click', async () => {
  const token = prompt('Zadaj PyPI API token:');
  if (!token) return;
  showToast('⏳ Publikujem na PyPI...', 10000);
  const result = await callApi('/publish/pypi', 'POST', { token });
  if (result && result.status === 'ok') {
    showToast('✅ Publikované na PyPI!', 5000, 'success');
  } else {
    showToast('❌ Chyba: ' + (result?.errors || result?.error || 'neznáma chyba'), 6000, 'error');
  }
});

document.getElementById('btnReset').addEventListener('click', () => {
  if (confirm('Naozaj reset?')) { showToast('🗑️ Reset...', 2000); setTimeout(loadReport, 500); }
});

document.getElementById('btnHistory').addEventListener('click', () => {
  const el = document.getElementById('detailHistory');
  if (el.open) el.open = false;
  else { el.open = true; loadHistory(); }
});

// --- Dropzone ---
dropzone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => {
  if (e.target.files[0]) {
    const reader = new FileReader();
    reader.onload = (ev) => {
      try { const data = JSON.parse(ev.target.result); currentData = data; render(data); dropzone.style.display = 'none'; errorEl.style.display = 'none'; contentEl.style.display = 'block'; } catch (err) { showToast('Chyba: '+err.message, 4000, 'error'); }
    };
    reader.readAsText(e.target.files[0]);
  }
});

// --- Spustenie ---
loadReport();
</script>
</body>
</html>
DASH_EOF
echo "[OK] dashboard/index.html – kompletné rozhranie s rozbaľovacími sekciami"

# 5. Spustenie API servera (ak nebeží)
echo ""
echo "=== OVERENIE API SERVERA ==="
if pgrep -f "server.api" > /dev/null; then
    echo "✅ API server už beží"
else
    echo "🚀 Spúšťam API server na porte 8765..."
    nohup python3 -c "from server.api import run_server; run_server(host='0.0.0.0', port=8765)" > api.log 2>&1 &
    sleep 2
    echo "✅ API server spustený"
fi

echo ""
echo "=============================================================="
echo "   HOTOVO! Dashboard je pripravený."
echo "=============================================================="
echo ""
echo "Obnov stránku dashboardu (F5) a uvidíš:"
echo "  - Rozbaľovacie sekcie pre nálezy, CVE, históriu"
echo "  - Tlačidlá zoskupené v toolbar (Sken, Opravy, Export, PyPI)"
echo "  - Reálny trend z histórie (ak existuje)"
echo "  - Profesionálny vzhľad s ozubenými kolesami"
echo ""
echo "API endpointy:"
echo "  GET  /history – história skenov"
echo "  GET  /stats – štatistiky"
echo "  POST /publish/pypi – publikácia na PyPI (vyžaduje token)"
echo "  POST /export/pdf – export reportu ako PDF"
echo ""
echo "Ak chceš pridať token do PyPI, stačí kliknúť na tlačidlo Publikovať."
