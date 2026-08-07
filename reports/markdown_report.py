from typing import Any, Dict, List


def generate(result: Dict[str, Any], output_path: str) -> None:
    lines: List[str] = []
    lines.append(
        f"# ForensicSuite Report v{result.get('version', '1.0.0')} – {result['project_path']}"
    )
    lines.append("")
    lines.append(f"**Súborov:** {result['file_count']}  ")
    lines.append(f"**Dátum:** {result.get('timestamp', 'N/A')}")
    lines.append("")

    lines.append("## Skóre")
    lines.append("")
    for name, data in result.get("scores", {}).items():
        score = data.get("score")
        score_text = "N/A" if score is None else f"{score}/100"
        lines.append(f"- **{name}**: {score_text}")
        if "details" in data:
            for k, v in data["details"].items():
                lines.append(f"  - {k}: {v}")
    lines.append("")

    for plugin_name, plugin_result in result.get("plugins", {}).items():
        lines.append(f"## Plugin: {plugin_name}")
        lines.append("")
        if plugin_result["status"] != "ok":
            lines.append(
                f"⚠️ Zlyhal: {plugin_result.get('error', plugin_result.get('reason', 'unknown'))}"
            )
            lines.append("")
            continue
        data = plugin_result["data"]
        if plugin_name == "filesystem":
            lines.append(f"- Celková veľkosť: {data['total_size_bytes']} bajtov")
            lines.append(f"- Prázdne súbory: {len(data['empty_files'])}")
            lines.append(f"- Duplicitné skupiny: {len(data['duplicate_groups'])}")
            lines.append(f"- Orphaned obrázky: {len(data['orphaned_images'])}")
        elif plugin_name == "python":
            lines.append(f"- Python súbory: {data['file_count']}")
            lines.append(f"- Celkové LOC: {data['total_loc']}")
            lines.append(f"- Priemerná komplexita: {data['avg_function_complexity']}")
            lines.append(f"- Cyklické importy: {len(data['cyclic_imports'])}")
            lines.append(f"- Možný dead code: {len(data['dead_code_candidates'])}")
            cve = data.get("cve_report", {})
            lines.append(
                f"- CVE kontrola: {cve.get('status')} ({len(cve.get('vulnerabilities', []))} zraniteľností)"
            )
        elif plugin_name == "secrets":
            lines.append(f"- Nájdené secrets: {data['findings_count']}")
            for finding in data.get("findings", [])[:10]:
                lines.append(
                    f"  - `{finding['file']}:{finding['line']}` ({finding['type']}): `{finding['snippet']}`"
                )
        elif plugin_name == "shell":
            lines.append(f"- Analyzované skripty: {data['scripts_analyzed']}")
            lines.append(f"- Nálezy: {data['findings_count']}")
            for finding in data.get("findings", [])[:10]:
                lines.append(
                    f"  - `{finding['file']}:{finding['line']}` ({finding['type']}): `{finding['content']}`"
                )
        elif plugin_name == "git":
            lines.append(f"- Branch: {data.get('branch', 'N/A')}")
            lines.append(f"- Commits: {data.get('commit_count', 'N/A')}")
            lines.append(f"- Posledný commit: {data.get('last_commit', 'N/A')}")
            lines.append(
                f"- Nepotvrdené zmeny: {'áno' if data.get('uncommitted_changes') else 'nie'}"
            )
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
