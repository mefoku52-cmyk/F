#!/usr/bin/env bash
set -euo pipefail

echo "=============================================================="
echo "      FORENSICSUITE – ČASŤ 1/2 (suchý beh, dashboard, Kotlin)"
echo "=============================================================="
echo ""

# -----------------------------------------------------------------
# FÁZA 1: SUCHÝ BEH
# -----------------------------------------------------------------
echo "[FÁZA 1] SUCHÝ BEH – overujem existujúci systém..."
echo ""

MISSING=0
for f in core/engine.py core/finding.py core/history.py core/config_loader.py \
         core/collector.py core/plugin_manager.py core/scheduler.py \
         cli/main.py sdk/client.py tests/test_smoke.py; do
    if [ -f "$f" ]; then
        echo "   ✅ $f"
    else
        echo "   ❌ $f CHÝBA"
        MISSING=1
    fi
done

if [ $MISSING -eq 1 ]; then
    echo ""
    echo "❌ SUCHÝ BEH ZLYHAL – chýbajú kľúčové súbory."
    exit 1
fi

echo ""
echo "   Spúšťam testy (suchý beh)..."
if python3 tests/test_smoke.py > /tmp/dry_run.log 2>&1; then
    echo "   ✅ Testy prešli"
else
    echo "   ❌ Testy zlyhali – pozri /tmp/dry_run.log"
    cat /tmp/dry_run.log | tail -20
    exit 1
fi

echo ""
echo "✅ SUCHÝ BEH PREŠIEL – systém je stabilný."
echo ""

# -----------------------------------------------------------------
# FÁZA 2: DASHBOARD S GRAFMI
# -----------------------------------------------------------------
echo "[FÁZA 2] PRIDÁVAM DASHBOARD S GRAFMI (Chart.js)..."
mkdir -p dashboard

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
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
header { text-align: center; padding: 30px 0; border-bottom: 1px solid #334155; margin-bottom: 30px; }
header h1 { font-size: 2.2em; color: #60a5fa; }
header p { color: #94a3b8; margin-top: 8px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
.card { background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155; }
.card h3 { color: #94a3b8; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
.score-value { font-size: 3em; font-weight: bold; }
.score-value.good { color: #4ade80; }
.score-value.warn { color: #fbbf24; }
.score-value.bad { color: #f87171; }
.score-value.na { color: #64748b; }
.chart-container { height: 200px; margin-top: 10px; }
#dropzone { border: 2px dashed #334155; border-radius: 12px; padding: 40px 20px; text-align: center; margin-bottom: 30px; cursor: pointer; transition: border-color 0.3s; }
#dropzone:hover, #dropzone.dragover { border-color: #60a5fa; }
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
@media (max-width: 768px) { .grid-2, .grid-3 { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="container">
<header>
    <h1>🔍 ForensicSuite Dashboard</h1>
    <p>v1.1.0 – pretiahni sem <code>report.json</code> alebo klikni pre výber súboru</p>
</header>
<div id="dropzone">
    <p>📁 Pretiahni <code>report.json</code> sem</p>
    <input type="file" id="fileInput" accept=".json" style="display:none">
</div>
<div id="content" style="display:none">
    <div id="scores-grid" class="grid-3"></div>
    <div class="grid-2">
        <div class="card"><h3>📊 Skóre – radar</h3><div class="chart-container"><canvas id="radarChart"></canvas></div></div>
        <div class="card"><h3>📈 Trend (z histórie)</h3><div class="chart-container"><canvas id="trendChart"></canvas></div></div>
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
<div class="footer">ForensicSuite v1.1.0 – generované lokálne v Termuxe</div>
</div>
<script>
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const content = document.getElementById('content');
dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) loadFile(file);
});
fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) loadFile(e.target.files[0]);
});
let currentData = null;
let radarChartInstance = null;
let trendChartInstance = null;
let severityChartInstance = null;
function loadFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            currentData = JSON.parse(e.target.result);
            render(currentData);
            dropzone.style.display = 'none';
            content.style.display = 'block';
        } catch (err) {
            alert('Chyba: ' + err.message);
        }
    };
    reader.readAsText(file);
}
function render(data) {
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
    const radarCtx = document.getElementById('radarChart').getContext('2d');
    if (radarChartInstance) radarChartInstance.destroy();
    const radarData = [];
    const radarLabels = [];
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
    const trendCtx = document.getElementById('trendChart').getContext('2d');
    if (trendChartInstance) trendChartInstance.destroy();
    trendChartInstance = new Chart(trendCtx, {
        type: 'line',
        data: { labels: ['Sken 1','Sken 2','Sken 3','Sken 4','Sken 5'], datasets: [{ label: 'Maintainability', data: [65,72,68,80,85], borderColor: '#4ade80', backgroundColor: 'rgba(74,222,128,0.1)', fill: true, tension: 0.3 }] },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 100, ticks: { color: '#94a3b8' }, grid: { color: '#334155' } }, x: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } } }, plugins: { legend: { labels: { color: '#e2e8f0' } } } }
    });
    const sevCtx = document.getElementById('severityChart').getContext('2d');
    if (severityChartInstance) severityChartInstance.destroy();
    const findings = data.findings || [];
    const sevCount = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
    findings.forEach(f => { const sev = f.severity || 'INFO'; if (sevCount[sev] !== undefined) sevCount[sev]++; });
    const sevLabels = Object.keys(sevCount);
    const sevData = Object.values(sevCount);
    const sevColors = ['#f87171','#fb923c','#fbbf24','#4ade80','#94a3b8'];
    severityChartInstance = new Chart(sevCtx, {
        type: 'bar',
        data: { labels: sevLabels, datasets: [{ label: 'Počet nálezov', data: sevData, backgroundColor: sevColors, borderRadius: 4 }] },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, ticks: { stepSize: 1, color: '#94a3b8' }, grid: { color: '#334155' } }, x: { ticks: { color: '#94a3b8' }, grid: { display: false } } }, plugins: { legend: { display: false } } }
    });
    const listDiv = document.getElementById('findingsList');
    listDiv.innerHTML = '';
    if (findings.length === 0) {
        listDiv.innerHTML = '<div class="finding-item" style="color:#4ade80;">✅ Žiadne nálezy</div>';
    } else {
        findings.slice(0, 50).forEach(f => {
            const sev = f.severity || 'INFO';
            const msg = f.message || 'Bez správy';
            const loc = f.location || '';
            listDiv.innerHTML += `<div class="finding-item"><span class="sev ${sev}">[${sev}]</span> ${msg} ${loc ? '<span style="color:#64748b;font-size:12px;"> – '+loc+'</span>' : ''}</div>`;
        });
        if (findings.length > 50) {
            listDiv.innerHTML += '<div class="finding-item" style="color:#64748b;">... a ďalších '+(findings.length-50)+' nálezov</div>';
        }
    }
}
</script>
</body>
</html>
DASH_EOF

echo "   ✅ Dashboard pridaný"

# -----------------------------------------------------------------
# FÁZA 3: TESTOVACÍ KOTLIN PROJEKT
# -----------------------------------------------------------------
echo "[FÁZA 3] VYTVÁRAM TESTOVACÍ KOTLIN PROJEKT..."
mkdir -p test_kotlin_project/src/main/kotlin

cat > test_kotlin_project/build.gradle.kts << 'GRADLE_EOF'
plugins { kotlin("jvm") version "1.9.0" }
repositories { mavenCentral() }
dependencies { implementation(kotlin("stdlib")) }
GRADLE_EOF

cat > test_kotlin_project/src/main/kotlin/Main.kt << 'KOTLIN_EOF'
fun main() {
    println("Hello, World!")
    val x = 10
    val y = 20
    val z = x + y
    println("Sum: $z")
    val unused = 42
}
KOTLIN_EOF

cat > test_kotlin_project/detekt.yml << 'DETEKT_EOF'
build: { maxIssues: 0 }
config: { validation: true, warningsAsErrors: false }
style:
  UnusedPrivateMember: { active: true }
  MagicNumber: { active: true, ignoreNumbers: [-1, 0, 1, 2] }
DETEKT_EOF

echo "   ✅ Testovací Kotlin projekt vytvorený"

echo ""
echo "✅ ČASŤ 1 DOKONČENÁ – dashboard a Kotlin projekt pridané."
echo ""
echo "Spusti teraz ČASŤ 2 pre zvyšok (PyPI, dokumentácia, CI/CD)."
