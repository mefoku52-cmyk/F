import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

OSV_QUERYBATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_VULN_URL_TEMPLATE = "https://api.osv.dev/v1/vulns/{vuln_id}"


def check_dependencies(dependencies: List[Dict[str, str]], timeout: float = 10.0) -> Dict[str, Any]:
    if not dependencies:
        return {"status": "skipped", "reason": "žiadne závislosti na kontrolu", "vulnerabilities": []}

    queries = [
        {
            "package": {"name": dep["name"], "ecosystem": dep.get("ecosystem", "PyPI")},
            "version": dep["version"],
        }
        for dep in dependencies
        if dep.get("version")
    ]
    if not queries:
        return {"status": "skipped", "reason": "žiadne závislosti s presnou verziou", "vulnerabilities": []}

    body = json.dumps({"queries": queries}).encode("utf-8")
    request = urllib.request.Request(
        OSV_QUERYBATCH_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return {"status": "unavailable", "reason": f"OSV.dev API nedostupné: {e}", "vulnerabilities": []}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "unavailable", "reason": "OSV.dev vrátilo neplatný JSON", "vulnerabilities": []}

    batch_results = parsed.get("results", [])

    pending: List[Dict[str, Any]] = []
    for dep, result in zip(dependencies, batch_results):
        vuln_ids = [v.get("id") for v in result.get("vulns", []) if v.get("id")]
        for vuln_id in vuln_ids:
            pending.append({"dependency": dep["name"], "version": dep.get("version"), "vuln_id": vuln_id})

    if not pending:
        return {"status": "ok", "vulnerabilities": []}

    findings: List[Dict[str, Any]] = [None] * len(pending)
    max_workers = min(8, len(pending))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(_fetch_vuln_detail, item["vuln_id"], timeout): idx
            for idx, item in enumerate(pending)
        }
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            item = pending[idx]
            detail = future.result()
            findings[idx] = {
                "dependency": item["dependency"],
                "version": item["version"],
                "vuln_id": item["vuln_id"],
                "summary": detail.get("summary") if detail else None,
                "severity": detail.get("severity") if detail else None,
            }

    return {"status": "ok", "vulnerabilities": findings}


def _fetch_vuln_detail(vuln_id: str, timeout: float) -> Dict[str, Any]:
    url = OSV_VULN_URL_TEMPLATE.format(vuln_id=vuln_id)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            raw = response.read()
        return json.loads(raw)
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError):
        return {}

