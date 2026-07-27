from typing import Any, Dict, List

from core.finding import Finding


def score_architecture(
    findings: List[Finding],
    config: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Heuristické skóre architektúry (0-100) založené na findings.
    """
    config = config or {}
    weights = config.get("scoring_weights", {}).get("architecture", {})
    cycle_penalty = weights.get("cyclic_import_penalty_per_cycle", 15)
    orphan_penalty = weights.get("orphaned_file_penalty_per_file", 2)

    # Cyklické importy – extrahujeme z Python metrics
    cycles = []
    for f in findings:
        if f.plugin == "python" and f.message == "Python metrics":
            cycles = f.metadata.get("cyclic_imports", [])
            break

    # Orphaned images z filesystem findings
    orphaned = [f for f in findings if f.plugin == "filesystem" and "osamelý" in f.message.lower()]

    score = 100.0
    score -= min(len(cycles) * cycle_penalty, 60)
    score -= min(len(orphaned) * orphan_penalty, 20)
    score = max(0.0, round(score, 1))

    return {
        "score": score,
        "cyclic_import_count": len(cycles),
        "orphaned_file_count": len(orphaned),
        "details": {
            "cycle_penalty_per_cycle": cycle_penalty,
            "orphan_penalty_per_file": orphan_penalty,
        },
    }
