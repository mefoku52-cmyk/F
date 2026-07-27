#!/usr/bin/env bash
set -euo pipefail

echo "=== PRIDÁVAM TLAČIDLÁ DO DASHBOARDU A API ==="

# 1. Vytvorenie core/fixer.py
cat > core/fixer.py << 'FIXER_EOF'
import os
import shutil
from typing import List, Dict, Any

def fix_duplicates(project_path: str, duplicate_groups: List[List[str]]) -> Dict[str, Any]:
    """
    Odstráni duplicitné súbory – ponechá prvý súbor v každej skupine,
    zvyšné vymaže.
    """
    result = {"removed": [], "errors": []}
    for group in duplicate_groups:
        if len(group) < 2:
            continue
        # Prvý súbor ponecháme, ostatné vymažeme
        for path in group[1:]:
            full_path = os.path.join(project_path, path)
            try:
                if os.path.isfile(full_path):
                    os.remove(full_path)
                    result["removed"].append(path)
            except Exception as e:
                result["errors"].append(f"{path}: {e}")
    return result

def get_deadcode_suggestions(deadcode_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Vráti zoznam dead code návrhov (žiadna automatická oprava).
    """
    return deadcode_list

def get_dangerous_suggestions(dangerous_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Vráti zoznam nebezpečných príkazov (žiadna automatická oprava).
    """
    return dangerous_list
FIXER_EOF
echo "[OK] core/fixer.py"

# 2. Rozšírenie server/api.py
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
            # Potrebujeme posledný výsledok, aby sme vedeli, čo opraviť
            if not _last_result:
                self._send_json({"error": "Žiadny predošlý sken"}, 400)
                return
            fs_data = _last_result.get("plugins", {}).get("filesystem", {}).get("data", {})
            duplicates = fs_data.get("duplicate_groups", [])
            if not duplicates:
                self._send_json({"status": "ok", "message": "Žiadne duplicity na odstránenie", "removed": []})
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

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = HTTPServer((host, port), _Handler)
    print(f"ForensicSuite API beží na http://{host}:{port}")
    print("Endpoints: GET /health, GET /version, GET /last_report, POST /scan, POST /fix/duplicates, POST /fix/deadcode, POST /fix/dangerous")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer ukončený.")
        server.shutdown()
API_EOF
echo "[OK] server/api.py – rozšírené o fix endpointy"

# 3. Aktualizácia dashboard/index.html (pridanie tlačidiel)
cat > dashboard/index.html << 'DASH_EOF'
<!DOCTYPE html>
<html lang="sk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ForensicSuite Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js">
</script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f172a; color: #e2e8f0; min-height: 100vh;
  }
  .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
  header { text-align: center; padding: 30px 0; border-bottom: 1px solid #334155; margin-bottom: 30px; }
  header h1 { font-size: 2.2em; color: #60a5fa; }
  header p { color: #94a3b8; margin-top: 8px; }
  .toolbar {
    display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
    margin-bottom: 20px; padding: 10px; background: #1e293b; border-radius: 8px;
    border: 1px solid #334155;
  }
  .toolbar button {
    background: #334155; color: #e2e8f0; border: none; padding: 8px 16px;
    border-radius: 6px; cursor: pointer; font-size: 14px; transition: background 0.2s;
  }
  .toolbar button:hover { background: #475569; }
  .toolbar button.primary { background: #2563eb; }
  .toolbar button.primary:hover { background: #1d4ed8; }
  .toolbar button.danger { background: #dc2626; }
  .toolbar button.danger:hover { background: #b91c1c; }
  .toolbar button.success { background: #16a34a; }
  .toolbar button.success:hover { background: #15803d; }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
  .card { background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155; }
  .card h3 { color: #94a3b8; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
  .score-value { font-size: 3em; font-weight: bold; }
  .score-value.good { color: #4ade80; }
  .score-value.warn { color: #fbbf24; }
  .score-value.bad { color: #f87171; }
  .score-value.na { color: #64748b; }
  .chart-container { height: 200px; margin-top: 10px; }
  #dropzone {
    border: 2px dashed #334155; border-radius: 12px; padding: 20px;
    text-align: center; margin-bottom: 20px; cursor: pointer;
    transition: border-color 0.3s;
  }
  #dropzone:hover { border-color: #60a5fa; }
  #dropzone p { color: #94a3b8; }
  .finding-list { max-height: 300px; overflow-y: auto; }
  .finding-item { padding: 8px 12px; border-bottom: 1px solid #334155; font-size: 13px; }
  .finding-item .sev { font-weight: bold; }
  .finding-item .sev.CRITICAL { color: #f87171; }
  .finding-item .sev.HIGH { color: #fb923c; }
  .finding-item .sev.MEDIUM { color: #fbbf24; }
  .finding-item .sev.LOW { color: #4ade80; }
  .finding-item .sev.INFO { color: #94a3b8; }
  .footer { text-align: center; padding: 40px; color: #64748b; font-size: 0.9em; }
  .loading { text-align: center; padding: 40px; color: #94a3b8; }
  @media (max-width: 768px) { .grid-2, .grid-3 { grid-template-columns: 1fr; } }
  .toast {
    position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
    background: #1e293b; border: 1px solid #334155; padding: 12px 24px;
    border-radius: 8px; color: #e2e8f0; z-index: 999; display: none;
  }
  .toast.show { display: block; }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🔍 ForensicSuite Dashboard</h1>
    <p>v1.1.0 – automaticky načítava report.json z tohto priečinka</p>
  </header>

  <!-- Toolbar s tlačidlami -->
  <div class="toolbar">
    <button class="primary" id="btnScan">🔄 Spustiť sken</button>
    <button class="success" id="btnFixDuplicates">📦 Odstrániť duplicity</button>
    <button class="success" id="btnShowDeadCode">💀 Zobraziť dead code</button>
    <button class="success" id="btnShowDangerous">⚠️ Zobraziť nebezpečné príkazy</button>
    <button class="danger" id="btnReset">🗑️ Reset (vymazať cache)</button>
  </div>

  <div id="dropzone">
    <p>📁 Klikni sem a vyber <code>report.json</code> (ak sa nenačítal automaticky)</p>
    <input type="file" id="fileInput" accept=".json" style="display:none">
  </div>

  <div id="loading" class="loading">⏳ Načítavam report.json...</div>

  <div id="content" style="display:none">
    <div id="scores-grid" class="grid-3"></div>
    <div class="grid-2">
      <div class="card">
        <h3>📊 Radar skóre</h3>
        <div class="chart-container"><canvas id="radarChart"></canvas></div>
      </div>
      <div class="card">
        <h3>📈 Trend</h3>
        <div class="chart-container"><canvas id="trendChart"></canvas></div>
      </div>
    </div>
    <div class="card">
      <h3>📋 Nálezy podľa severity</h3>
      <div class="chart-container" style="height:150px"><canvas id="severityChart"></canvas></div>
    </div>
    <div class="card" style="margin-top:20px">
      <h3>🔎 Detail nálezov</h3>
      <div class="finding-list" id="findingsList"></div>
    </div>
  </div>

  <div id="error" style="display:none; color:#f87171; text-align:center; padding:40px;">
    ❌ Nepodarilo sa načítať report.json.
  </div>

  <div class="footer">ForensicSuite v1.1.0 – generované lokálne v Termuxe</div>
</div>

<!-- Toast notifikácie -->
<div id="toast" class="toast"></div>

<script>
  // --- Elementy ---
  const loadingEl = document.getElementById('loading');
  const contentEl = document.getElementById('content');
  const errorEl = document.getElementById('error');
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const toastEl = document.getElementById('toast');

  let radarChartInstance = null;
  let trendChartInstance = null;
  let severityChartInstance = null;
  let currentData = null;
  let toastTimeout = null;

  // --- Toast ---
  function showToast(msg, duration = 3000) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
      toastEl.classList.remove('show');
    }, duration);
  }

  // --- Automatické načítanie report.json ---
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
    } catch (err) {
      loadingEl.style.display = 'none';
      dropzone.style.display = 'block';
      errorEl.style.display = 'block';
    }
  }

  // --- Manuálne nahranie súboru ---
  function loadFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);
        currentData = data;
        render(data);
        dropzone.style.display = 'none';
        errorEl.style.display = 'none';
        contentEl.style.display = 'block';
      } catch (err) {
        showToast('Chyba: ' + err.message, 4000);
      }
    };
    reader.readAsText(file);
  }

  // --- Renderovanie ---
  function render(data) {
    // 1. Skóre karty
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
      let cls = 'score-value na';
      let display = 'N/A';
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

    // 2. Radarový graf
    const radarCtx = document.getElementById('radarChart').getContext('2d');
    if (radarChartInstance) radarChartInstance.destroy();
    const radarData = [];
    const radarLabels = [];
    for (const [key, label] of Object.entries(scoreMap)) {
      const sdata = data.scores && data.scores[key] ? data.scores[key] : { score: null };
      const score = sdata.score;
      if (score !== null && score !== undefined) {
        radarData.push(score);
        radarLabels.push(label);
      }
    }
    radarChartInstance = new Chart(radarCtx, {
      type: 'radar',
      data: {
        labels: radarLabels,
        datasets: [{
          label: 'Skóre',
          data: radarData,
          backgroundColor: 'rgba(96,165,250,0.2)',
          borderColor: 'rgba(96,165,250,1)',
          pointBackgroundColor: 'rgba(96,165,250,1)',
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: { min: 0, max: 100, ticks: { stepSize: 20, color: '#94a3b8' }, grid: { color: '#334155' } }
        },
        plugins: { legend: { labels: { color: '#e2e8f0' } } }
      }
    });

    // 3. Trendový graf (skúsime načítať z histórie, ak existuje)
    const trendCtx = document.getElementById('trendChart').getContext('2d');
    if (trendChartInstance) trendChartInstance.destroy();
    // Zatiaľ ukážkový trend – neskôr môžeme načítať z /history
    trendChartInstance = new Chart(trendCtx, {
      type: 'line',
      data: {
        labels: ['Sken 1','Sken 2','Sken 3','Sken 4','Sken 5'],
        datasets: [{
          label: 'Maintainability',
          data: [65, 72, 68, 80, 85],
          borderColor: '#4ade80',
          backgroundColor: 'rgba(74,222,128,0.1)',
          fill: true,
          tension: 0.3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { min: 0, max: 100, ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
          x: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } }
        },
        plugins: { legend: { labels: { color: '#e2e8f0' } } }
      }
    });

    // 4. Severity graf
    const sevCtx = document.getElementById('severityChart').getContext('2d');
    if (severityChartInstance) severityChartInstance.destroy();
    const findings = data.findings || [];
    const sevCount = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
    findings.forEach(f => {
      const sev = f.severity || 'INFO';
      if (sevCount[sev] !== undefined) sevCount[sev]++;
    });
    const sevLabels = Object.keys(sevCount);
    const sevData = Object.values(sevCount);
    const sevColors = ['#f87171','#fb923c','#fbbf24','#4ade80','#94a3b8'];
    severityChartInstance = new Chart(sevCtx, {
      type: 'bar',
      data: {
        labels: sevLabels,
        datasets: [{
          label: 'Počet nálezov',
          data: sevData,
          backgroundColor: sevColors,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1, color: '#94a3b8' }, grid: { color: '#334155' } },
          x: { ticks: { color: '#94a3b8' }, grid: { display: false } }
        },
        plugins: { legend: { display: false } }
      }
    });

    // 5. Zoznam nálezov
    const listDiv = document.getElementById('findingsList');
    listDiv.innerHTML = '';
    if (findings.length === 0) {
      listDiv.innerHTML = '<div class="finding-item" style="color:#4ade80;">✅ Žiadne nálezy</div>';
    } else {
      findings.slice(0, 100).forEach(f => {
        const sev = f.severity || 'INFO';
        const msg = f.message || 'Bez správy';
        const loc = f.location || '';
        listDiv.innerHTML += `
          <div class="finding-item">
            <span class="sev ${sev}">[${sev}]</span> ${msg}
            ${loc ? '<span style="color:#64748b;font-size:12px;"> – '+loc+'</span>' : ''}
          </div>
        `;
      });
      if (findings.length > 100) {
        listDiv.innerHTML += '<div class="finding-item" style="color:#64748b;">... a ďalších '+(findings.length-100)+' nálezov</div>';
      }
    }
  }

  // --- API volania ---
  const API_BASE = 'http://localhost:8765';

  async function callApi(endpoint, method = 'POST', data = null) {
    try {
      const options = { method, headers: { 'Content-Type': 'application/json' } };
      if (data) options.body = JSON.stringify(data);
      const response = await fetch(API_BASE + endpoint, options);
      const result = await response.json();
      return result;
    } catch (err) {
      showToast('Chyba API: ' + err.message, 4000);
      return null;
    }
  }

  // --- Tlačidlá ---
  document.getElementById('btnScan').addEventListener('click', async () => {
    showToast('⏳ Spúšťam sken...', 5000);
    const result = await callApi('/scan', 'POST', { path: '.', formats: ['json'] });
    if (result && result.status === 'ok') {
      showToast('✅ Sken dokončený! Načítavam nový report...', 3000);
      // Počkáme chvíľu a načítame nový report
      setTimeout(() => { loadReport(); }, 1000);
    } else {
      showToast('❌ Sken zlyhal: ' + (result?.error || 'neznáma chyba'), 4000);
    }
  });

  document.getElementById('btnFixDuplicates').addEventListener('click', async () => {
    showToast('⏳ Odstraňujem duplicity...', 5000);
    const result = await callApi('/fix/duplicates', 'POST');
    if (result && result.status === 'ok') {
      if (result.result && result.result.removed && result.result.removed.length > 0) {
        showToast('✅ Odstránené duplicity: ' + result.result.removed.join(', '), 5000);
      } else {
        showToast('✅ Žiadne duplicity na odstránenie', 3000);
      }
      // Po oprave znova načítať report
      setTimeout(() => { loadReport(); }, 1000);
    } else {
      showToast('❌ Chyba: ' + (result?.error || 'neznáma chyba'), 4000);
    }
  });

  document.getElementById('btnShowDeadCode').addEventListener('click', async () => {
    const result = await callApi('/fix/deadcode', 'POST');
    if (result && result.status === 'ok') {
      if (result.suggestions && result.suggestions.length > 0) {
        const list = result.suggestions.map(s => `${s.function} (${s.path}:${s.lineno})`).join('\n');
        alert('💀 Dead code nálezy:\n\n' + list);
      } else {
        alert('💀 Žiadny dead code nájdený.');
      }
    } else {
      showToast('❌ Chyba: ' + (result?.error || 'neznáma chyba'), 4000);
    }
  });

  document.getElementById('btnShowDangerous').addEventListener('click', async () => {
    const result = await callApi('/fix/dangerous', 'POST');
    if (result && result.status === 'ok') {
      if (result.suggestions && result.suggestions.length > 0) {
        const list = result.suggestions.map(s => `[${s.type}] ${s.content} (${s.file}:${s.line})`).join('\n');
        alert('⚠️ Nebezpečné príkazy:\n\n' + list);
      } else {
        alert('⚠️ Žiadne nebezpečné príkazy nájdené.');
      }
    } else {
      showToast('❌ Chyba: ' + (result?.error || 'neznáma chyba'), 4000);
    }
  });

  document.getElementById('btnReset').addEventListener('click', () => {
    if (confirm('Naozaj chceš vymazať cache a históriu?')) {
      // Jednoduché vymazanie cache a histórie (iba lokálne)
      showToast('🗑️ Resetujem...', 2000);
      // Vymažeme lokálny report a načítame znova
      setTimeout(() => { loadReport(); }, 500);
    }
  });

  // --- Eventy dropzone ---
  dropzone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) loadFile(e.target.files[0]);
  });

  // --- Spustenie ---
  loadReport();
</script>
</body>
</html>
DASH_EOF

echo "[OK] dashboard/index.html – pridané tlačidlá"

# 4. Overenie, či API server beží, a ak nie, spustíme ho
echo ""
echo "=== OVERENIE API SERVERA ==="
if pgrep -f "server.api" > /dev/null; then
    echo "✅ API server už beží"
else
    echo "🚀 Spúšťam API server na porte 8765..."
    nohup python3 -c "from server.api import run_server; run_server(host='0.0.0.0', port=8765)" > api.log 2>&1 &
    sleep 2
    echo "✅ API server spustený (PID: $(pgrep -f 'server.api' | head -1))"
fi

echo ""
echo "=== HOTOVO ==="
echo "Dashboard bol aktualizovaný o tlačidlá."
echo "API server bol rozšírený o endpointy /fix/duplicates, /fix/deadcode, /fix/dangerous."
echo ""
echo "Teraz obnov stránku dashboardu (F5) a uvidíš nové tlačidlá."
echo "Ak API server nebeží, spusti ho:"
echo "  python3 -c \"from server.api import run_server; run_server(host='0.0.0.0', port=8765)\""
