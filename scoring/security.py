from typing import Any, Dict, List

from core.finding import Finding, Severity


def score_security(
    findings: List[Finding],
    config: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Heuristické bezpečnostné skóre (0-100) založené na findings.
    """
    config = config or {}
    weights = config.get("scoring_weights", {}).get("security", {})
    vuln_penalty = weights.get("vuln_penalty_per_cve", 20)
    secret_penalty = weights.get("secret_penalty_per_finding", 10)
    secret_cap = weights.get("secret_penalty_cap", 50)

    # CVE nálezy (severity CRITICAL od python pluginu)
    cve_findings = [f for f in findings if f.plugin == "python" and f.severity == Severity.CRITICAL and "CVE" in f.message]
    vuln_count = len(cve_findings)

    # Secrets nálezy (severity HIGH/CRITICAL od secrets pluginu)
    secret_findings = [f for f in findings if f.plugin == "secrets"]
    secret_count = len(secret_findings)

    penalty = vuln_count * vuln_penalty
    penalty += min(secret_count * secret_penalty, secret_cap)

    score = max(0.0, round(100.0 - penalty, 1))

    return {
        "score": score,
        "vulnerability_count": vuln_count,
        "secret_findings_count": secret_count,
        "cve_status": "ok" if vuln_count > 0 else "skipped",
        "vulnerabilities": [f.metadata.get("vuln", {}) for f in cve_findings],
        "secrets": [f.metadata for f in secret_findings[:10]],
        "details": {
            "vuln_penalty_per_cve": vuln_penalty,
            "secret_penalty_per_finding": secret_penalty,
            "secret_penalty_cap": secret_cap,
        },
    }
