"""
Generuje statický HTML report s prehľadnými sekciami.
Nepotrebuje externé závislosti (žiadny Jinja2).

Vstupy z `result` (názvy pluginov, skóre, dáta z pluginov) sú nedôveryhodné
(pochádzajú z analyzovaného projektu), preto sa všetok text vkladaný do HTML
escapuje pomocou `html.escape`, aby sa zabránilo XSS pri otvorení reportu
v prehliadači.
"""

import html
import json
from typing import Any, Dict


def _esc(value: Any) -> str:
    """Bezpečne escapuje ľubovoľnú hodnotu pre vloženie do HTML."""
    return html.escape(str(value), quote=True)


def generate(result: Dict[str, Any], output_path: str) -> None:
    scores = result.get("scores", {})
    plugins = result.get("plugins", {})

    score_html = ""
    for name, data in scores.items():
        score = data.get("score")
        color = (
            "#4caf50"
            if score and score >= 80
            else "#ff9800" if score and score >= 50 else "#f44336"
        )
        score_text = "N/A" if score is None else f"{score}"
        score_html += f"""
        <div class="score-card">
            <h3>{_esc(name)}</h3>
            <div class="score-value" style="color:{color}">{_esc(score_text)}</div>
            <div class="score-max">/ 100</div>
        </div>
        """

    plugin_html = ""
    for pname, pdata in plugins.items():
        status = pdata.get("status", "unknown")
        status_color = (
            "#4caf50"
            if status == "ok"
            else "#f44336" if status == "error" else "#9e9e9e"
        )
        raw_data = json.dumps(pdata.get("data", {}), indent=2, ensure_ascii=False)[:2000]
        plugin_html += f"""
        <div class="plugin-section">
            <h4>{_esc(pname)} <span class="badge" style="background:{status_color}">{_esc(status)}</span></h4>
            <pre>{_esc(raw_data)}</pre>
        </div>
        """

    project_path = _esc(result.get("project_path", ""))
    file_count = _esc(result.get("file_count", 0))

    html_doc = f"""<!DOCTYPE html>
<html lang="sk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ForensicSuite Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
.header {{ background: #1a237e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
.scores {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
.score-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
.score-value {{ font-size: 48px; font-weight: bold; }}
.score-max {{ font-size: 18px; color: #666; }}
.plugin-section {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.badge {{ color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; margin-left: 10px; }}
pre {{ background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; white-space: pre-wrap; word-break: break-word; }}
h4 {{ margin-top: 0; }}
</style>
</head>
<body>
<div class="header">
    <h1>ForensicSuite Report</h1>
    <p>{project_path} | {file_count} súborov</p>
</div>
<div class="scores">
    {score_html}
</div>
{plugin_html}
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
