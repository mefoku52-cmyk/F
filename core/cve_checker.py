import urllib.request
import json
import time
from typing import Dict, Any, Optional

class CVEChecker:
    def __init__(self):
        self.base_url = "https://api.osv.dev/v1/query"
        self.timeout = 10
    
    def check_package(self, package: str, version: str) -> Dict[str, Any]:
        """Skontroluje zraniteľnosti pre daný balík."""
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
                "reason": f"OSV.dev API nedostupné: {e}",
                "package": package,
                "version": version
            }
    
    def check_url(self, url: str) -> Dict[str, Any]:
        """Kontrola zraniteľností pomocou URL."""
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
                "reason": f"URL nedostupné: {e}",
                "url": url
            }
