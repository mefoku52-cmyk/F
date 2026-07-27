from typing import Any, Dict, List

from core.finding import Finding, Severity, aggregate_findings


def score_maintainability(
    findings: List[Finding],
    config: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Heuristické skóre udržateľnosti (0-100) založené výhradne na findings.
    """
    config = config or {}
    weights = config.get("scoring_weights", {}).get("maintainability", {})
    complexity_cap = weights.get("complexity_penalty_cap", 40)
    duplicate_cap = weights.get("duplicate_penalty_cap", 20)
    unused_imports_cap = weights.get("unused_imports_penalty_cap", 15)

    # Extrahujeme metriky z findings
    metrics = None
    for f in findings:
        if f.plugin == "python" and f.message == "Python metrics":
            metrics = f.metadata
            break

    if metrics is None:
        return {"score": 0, "error": "Chýbajú Python metriky"}

    avg_complexity = metrics.get("avg_function_complexity", 0.0)
    unused_imports_total = metrics.get("unused_imports_total", 0)

    # Duplicity z filesystem findings
    dup_findings = [f for f in findings if f.plugin == "filesystem" and "duplicate" in f.message.lower()]
    duplicate_ratio = len(dup_findings) / max(1, len(findings))

    score = 100.0
    score -= min(avg_complexity * 3, complexity_cap)
    score -= min(duplicate_ratio * 100, duplicate_cap)
    score -= min(unused_imports_total * 0.5, unused_imports_cap)
    score = max(0.0, round(score, 1))

    return {
        "score": score,
        "avg_function_complexity": avg_complexity,
        "duplicate_file_ratio": round(duplicate_ratio, 3),
        "unused_imports_total": unused_imports_total,
        "details": {
            "complexity_penalty_cap": complexity_cap,
            "duplicate_penalty_cap": duplicate_cap,
            "unused_imports_penalty_cap": unused_imports_cap,
        },
    }
