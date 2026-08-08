import urllib.request
import json
import time
from typing import Dict, Any, Optional, List


class CVEChecker:
    def __init__(self):
        self.base_url = "https://api.osv.dev/v1/query"
        self.timeout = 10

    def check_package(self, package: str, version: str) -> Dict[str, Any]:
        """Skontroluje zranitelnosti pre dany balik."""
        request_data = {
            "package": {
                "name": package,
                "ecosystem": "PyPI"
            },
            "version": version
        }

        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(request_data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # nosec
                raw = response.read()
                data = json.loads(raw)
                return {
                    "status": "ok",
                    "vulnerabilities": data.get("vulns", []),
                    "package": package,
                    "version": version
                }
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            return {
                "status": "unavailable",
                "reason": f"OSV.dev API nedostupne: {e}",
                "package": package,
                "version": version
            }

    def check_url(self, url: str) -> Dict[str, Any]:
        """Kontrola zranitelnosti pomocou URL."""
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as response:  # nosec
                raw = response.read()
                return {
                    "status": "ok",
                    "content_length": len(raw),
                    "url": url
                }
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            return {
                "status": "unavailable",
                "reason": f"URL nedostupne: {e}",
                "url": url
            }

    def check_dependencies(self, dependencies: List[Dict[str, str]]) -> Dict[str, Any]:
        """Adapter: skontroluje zoznam zavislosti (list dictov s klucmi name/version)
        a vrati agregovany vysledok pouzitelny pluginmi (napr. python plugin)."""
        results = []
        vulnerable = []
        unavailable = []

        for dep in dependencies:
            name = dep.get("name") or dep.get("package")
            version = dep.get("version", "")
            if not name:
                continue

            result = self.check_package(name, version)
            results.append(result)

            if result.get("status") == "ok" and result.get("vulnerabilities"):
                vulnerable.append(result)
            elif result.get("status") == "unavailable":
                unavailable.append(result)

        return {
            "status": "ok",
            "total": len(results),
            "vulnerable_count": len(vulnerable),
            "unavailable_count": len(unavailable),
            "vulnerable": vulnerable,
            "unavailable": unavailable,
            "results": results
        }


def check_dependencies(dependencies: List[Dict[str, str]]) -> Dict[str, Any]:
    """Modulova funkcia (wrapper) pre spatnu kompatibilitu s pluginmi,
    ktore importuju check_dependencies priamo z core.cve_checker."""
    checker = CVEChecker()
    return checker.check_dependencies(dependencies)
