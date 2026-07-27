#!/usr/bin/env bash
set -euo pipefail

echo "=== OPRAVA DASHBOARDU – finálna verzia v2 ==="

# 1. Stiahnutie Chart.js lokálne (ak nie je dostupný)
echo "1. Sťahujem Chart.js lokálne..."
if [ ! -f "dashboard/chart.min.js" ]; then
    curl -L -o dashboard/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js 2>/dev/null || echo "⚠️ Curl zlyhal, skúšam wget..."
    wget -O dashboard/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js 2>/dev/null || echo "⚠️ Wget zlyhal"
    if [ -f "dashboard/chart.min.js" ]; then
        echo "   ✅ Chart.js stiahnutý"
    else
        echo "   ⚠️ Nepodarilo sa stiahnuť Chart.js, použijem CDN"
    fi
else
    echo "   ✅ Chart.js už existuje"
fi

# 2. Vytvorenie dashboard/index.html
cat > dashboard/index.html << 'HTML_EOF'
<!DOCTYPE html>
<html lang="sk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ForensicSuite Dashboard</title>
<!-- Lokálna kópia Chart.js -->
<script src="chart.min.js"></script>
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

  /* Logo na pozadí – celé meno, zlatá farba, vyššia opacita */
  .logo-bg {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) scale(1.3);
    pointer-events: none;
    z-index: 0;
    opacity: 0.07;
    font-size: 110px;
    font-weight: 900;
    color: #d4af37;
    text-align: center;
    letter-spacing: 8px;
    line-height: 1.2;
    text-shadow: 0 0 80px rgba(212, 175, 55, 0.15);
    user-select: none;
    white-space: nowrap;
    font-family: 'Times New Roman', serif;
  }
  .logo-bg small {
    display: block;
    font-size: 36px;
    font-weight: 300;
    letter-spacing: 14px;
    opacity: 0.8;
    margin-top: 8px;
    color: #d4af37;
  }

  /* Jemné ozubené kolesá */
  .gears-bg {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    z-index: 0;
    opacity: 0.02;
  }
  .gears-bg::before {
    content: '⚙⚙⚙';
    position: absolute;
    top: 8%;
    left: 3%;
    font-size: 180px;
    opacity: 0.4;
    color: #d4af37;
    transform: rotate(15deg);
  }
  .gears-bg::after {
    content: '⚙⚙⚙';
    position: absolute;
    bottom: 8%;
    right: 3%;
    font-size: 220px;
    opacity: 0.3;
    color: #d4af37;
    transform: rotate(-25deg);
  }

  .container {
    position: relative;
    z-index: 1;
    max-width: 1300px;
    margin: 0 auto;
    padding: 20px;
  }

  header {
    text-align: center;
    padding: 30px 0 20px;
    border-bottom: 1px solid rgba(30, 41, 59, 0.5);
    margin-bottom: 25px;
    position: relative;
  }
  header h1 {
    font-size: 2.4em;
    color: #60a5fa;
    font-weight: 700;
    letter-spacing: -0.5px;
  }
  header h1 span { color: #e2e8f0; }
  header p { color: #94a3b8; margin-top: 6px; font-size: 0.95em; }

  /* Toolbar */
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-bottom: 25px;
    padding: 12px 16px;
    background: rgba(30, 41, 59, 0.7);
    backdrop-filter: blur(8px);
    border-radius: 12px;
    border: 1px solid rgba(30, 41, 59, 0.5);
  }
  .toolbar .group {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    padding: 0 8px;
    border-right: 1px solid rgba(30, 41, 59, 0.5);
  }
  .toolbar .group:last-child { border-right: none; }
  .toolbar .group-label {
    font-size: 0.7em;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-right: 4px;
  }
  .toolbar button {
    background: #1e293b;
    color: #e2e8f0;
    border: 1px solid transparent;
    padding: 6px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.2s;
    white-space: nowrap;
  }
  .toolbar button:hover {
    background: #334155;
    border-color: #475569;
    transform: translateY(-1px);
  }
  .toolbar button.primary { background: #2563eb; }
  .toolbar button.primary:hover { background: #1d4ed8; border-color: #60a5fa; }
  .toolbar button.success { background: #16a34a; }
  .toolbar button.success:hover { background: #15803d; border-color: #4ade80; }
  .toolbar button.danger { background: #dc2626; }
  .toolbar button.danger:hover { background: #b91c1c; border-color: #f87171; }
  .toolbar button.warning { background: #d97706; }
  .toolbar button.warning:hover { background: #b45309; border-color: #fbbf24; }
  .toolbar button.info { background: #0891b2; }
  .toolbar button.info:hover { background: #0e7490; border-color: #22d3ee; }

  /* Karty */
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 25px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px; }
  .card {
    background: rgba(30, 41, 59, 0.85);
    backdrop-filter: blur(4px);
    border-radius: 14px;
    padding: 22px 24px;
    border: 1px solid rgba(30, 41, 59, 0.6);
    transition: all 0.2s;
  }
  .card:hover { border-color: #334155; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
  .card h3 {
    color: #94a3b8;
    font-size: 0.75em;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 10px;
  }
  .score-value { font-size: 2.8em; font-weight: 700; }
  .score-value.good { color: #4ade80; }
  .score-value.warn { color: #fbbf24; }
  .score-value.bad { color: #f87171; }
  .score-value.na { color: #64748b; }
  .chart-container { height: 200px; margin-top: 8px; }

  /* Rozbaľovacie sekcie */
  .detail-section {
    margin-top: 16px;
    border-top: 1px solid rgba(30, 41, 59, 0.5);
    padding-top: 14px;
  }
  .detail-section summary {
    cursor: pointer;
    color: #60a5fa;
    font-weight: 600;
    padding: 8px 0;
    font-size: 1.05em;
    list-style: none;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: color 0.2s;
  }
  .detail-section summary:hover { color: #93bbfc; }
  .detail-section summary::-webkit-details-marker { display: none; }
  .detail-section summary::before {
    content: '▶';
    font-size: 0.8em;
    transition: transform 0.2s;
    color: #60a5fa;
  }
  .detail-section[open] summary::before { transform: rotate(90deg); }
  .detail-section .content {
    padding: 12px 0 6px;
    max-height: 400px;
    overflow-y: auto;
  }
  .finding-item {
    padding: 6px 10px;
    border-bottom: 1px solid rgba(30, 41, 59, 0.3);
    font-size: 13px;
  }
  .finding-item .sev { font-weight: 600; }
  .finding-item .sev.CRITICAL { color: #f87171; }
  .finding-item .sev.HIGH { color: #fb923c; }
  .finding-item .sev.MEDIUM { color: #fbbf24; }
  .finding-item .sev.LOW { color: #4ade80; }
  .finding-item .sev.INFO { color: #94a3b8; }

  /* Toast */
  .toast {
    position: fixed;
    bottom: 30px;
    left: 50%;
    transform: translateX(-50%);
    background: #1e293b;
    border: 1px solid #334155;
    padding: 14px 28px;
    border-radius: 10px;
    color: #e2e8f0;
    z-index: 999;
    display: none;
    font-size: 14px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
    max-width: 90%;
    text-align: center;
  }
  .toast.show { display: block; }
  .toast.success { border-color: #16a34a; }
  .toast.error { border-color: #dc2626; }

  .footer {
    text-align: center;
    padding: 30px;
    color: #475569;
    font-size: 0.85em;
    border-top: 1px solid rgba(30, 41, 59, 0.5);
    margin-top: 25px;
  }
  .loading { text-align: center; padding: 60px 20px; color: #94a3b8; }

  #dropzone {
    border: 2px dashed rgba(30, 41, 59, 0.6);
    border-radius: 12px;
    padding: 25px;
    text-align: center;
    margin-bottom: 20px;
    cursor: pointer;
    transition: border-color 0.3s;
    background: rgba(30, 41, 59, 0.2);
  }
  #dropzone:hover { border-color: #60a5fa; }
  #dropzone p { color: #94a3b8; }

  @media (max-width: 768px) {
    .grid-2, .grid-3 { grid-template-columns: 1fr; }
    .toolbar .group { border-right: none; border-bottom: 1px solid rgba(30,41,59,0.5); padding-bottom: 6px; }
    .logo-bg { font-size: 50px; white-space: normal; }
    .logo-bg small { font-size: 18px; letter-spacing: 6px; }
  }
</style>
</head>
<body>

<!-- Logo na pozadí – celé meno, zlatá farba -->
<div class="logo-bg">
  RADOSLAV
  <small>ČORNANIČ</small>
</div>

<!-- Jemné ozubené kolesá -->
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

  <!-- Dropzone -->
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
  // Skóre karty
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

  // Radarový graf
  const radarCtx = document.getElementById('radarChart');
  if (!radarCtx) return;
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

  if (radarData.length > 0 && typeof Chart !== 'undefined') {
    radarChartInstance = new Chart(radarCtx.getContext('2d'), {
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
  } else if (radarData.length > 0) {
    // Fallback – zobraziť text
    document.getElementById('radarChart').parentElement.innerHTML = '<div style="color:#94a3b8;padding:20px;">Radar nie je dostupný (Chart.js chýba).</div>';
  }

  // Severity graf
  const sevCtx = document.getElementById('severityChart');
  if (sevCtx && severityChartInstance) severityChartInstance.destroy();
  if (sevCtx && typeof Chart !== 'undefined') {
    const findings = data.findings || [];
    const sevCount = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
    findings.forEach(f => {
      const sev = f.severity || 'INFO';
      if (sevCount[sev] !== undefined) sevCount[sev]++;
    });
    const sevLabels = Object.keys(sevCount);
    const sevData = Object.values(sevCount);
    const sevColors = ['#f87171','#fb923c','#fbbf24','#4ade80','#94a3b8'];
    severityChartInstance = new Chart(sevCtx.getContext('2d'), {
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
  }

  // Zoznam nálezov
  const listDiv = document.getElementById('findingsList');
  listDiv.innerHTML = '';
  const findings = data.findings || [];
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
  const cves = findings.filter(f => f.severity === 'CRITICAL' && (f.message || '').includes('CVE'));
  if (cves.length === 0) {
    cveList.innerHTML = '<div class="finding-item" style="color:#4ade80;">✅ Žiadne CVE</div>';
  } else {
    cves.forEach(c => {
      cveList.innerHTML += `<div class="finding-item"><span class="sev CRITICAL">[CRITICAL]</span> ${c.message}</div>`;
    });
  }
}

// --- Trend z histórie ---
function renderTrendFromHistory(history) {
  const trendCtx = document.getElementById('trendChart');
  if (!trendCtx) return;
  if (trendChartInstance) trendChartInstance.destroy();
  if (typeof Chart === 'undefined') {
    trendCtx.parentElement.innerHTML = '<div style="color:#94a3b8;padding:20px;">Trend nie je dostupný (Chart.js chýba).</div>';
    return;
  }
  if (!history || history.length < 1) {
    trendChartInstance = new Chart(trendCtx.getContext('2d'), {
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
    return;
  }
  const sorted = history.sort((a,b) => a.timestamp - b.timestamp);
  const labels = sorted.map(h => h.datetime ? h.datetime.slice(5,16) : '');
  const scores = sorted.map(h => h.scores?.maintainability?.score ?? 0);
  trendChartInstance = new Chart(trendCtx.getContext('2d'), {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Maintainability',
        data: scores,
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
        x: { ticks: { color: '#94a3b8', maxTicksLimit: 10 }, grid: { color: '#334155' } }
      },
      plugins: { legend: { labels: { color: '#e2e8f0' } } }
    }
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
      showToast('✅ Odstránené: ' + result.result.removed.join(', '), 5000, 'success');
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
  } else { showToast('❌ Chyba', 4000, 'error'); }
});

document.getElementById('btnShowDangerous').addEventListener('click', async () => {
  const result = await callApi('/fix/dangerous', 'POST');
  if (result && result.status === 'ok') {
    if (result.suggestions && result.suggestions.length > 0) {
      const list = result.suggestions.map(s => `[${s.type}] ${s.content} (${s.file}:${s.line})`).join('\n');
      alert('⚠️ Nebezpečné príkazy:\n\n' + list);
    } else { alert('⚠️ Žiadne nebezpečné príkazy.'); }
  } else { showToast('❌ Chyba', 4000, 'error'); }
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
      try {
        const data = JSON.parse(ev.target.result);
        currentData = data;
        render(data);
        dropzone.style.display = 'none';
        errorEl.style.display = 'none';
        contentEl.style.display = 'block';
      } catch (err) {
        showToast('Chyba: '+err.message, 4000, 'error');
      }
    };
    reader.readAsText(e.target.files[0]);
  }
});

// --- Spustenie ---
loadReport();
</script>
</body>
</html>
HTML_EOF

echo "[OK] dashboard/index.html – opravené logo (zlaté, celé meno), lokálny Chart.js"

# 3. Reštart API servera
echo ""
echo "=== REŠTART API SERVERA ==="
pkill -f "server.api" 2>/dev/null || true
nohup python3 -c "from server.api import run_server; run_server(host='0.0.0.0', port=8765)" > api.log 2>&1 &
sleep 2
echo "✅ API server spustený"

echo ""
echo "=== HOTOVO ==="
echo "Obnov stránku dashboardu (F5)."
echo "Logo by malo byť zlaté a celé viditeľné."
echo "Radar by mal fungovať (ak je Chart.js načítaný)."
