"""
Generuje statický HTML report s prehľadnými sekciami.
Nepotrebuje externé závislosti (žiadny Jinja2).
"""

import json
from typing import Any, Dict


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
            <h3>{name}</h3>
            <div class="score-value" style="color:{color}">{score_text}</div>
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
        plugin_html += f"""
        <div class="plugin-section">
            <h4>{pname} <span class="badge" style="background:{status_color}">{status}</span></h4>
            <pre>{json.dumps(pdata.get("data", {}), indent=2, ensure_ascii=False)[:2000]}</pre>
        </div>
        """

    html = f"""<!DOCTYPE html>
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
pre {{ background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; }}
h4 {{ margin-top: 0; }}
</style>
</head>
<body>
<div class="header">
    <h1>ForensicSuite Report</h1>
    <p>{result['project_path']} | {result['file_count']} súborov</p>
</div>
<div class="scores">
    {score_html}
</div>
{plugin_html}
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
