#!/usr/bin/env bash
set -euo pipefail

echo "=== VYTVÁRAM SDK PRE FORENSICSUITE ==="

# 1. Vytvorenie adresárovej štruktúry pre SDK
mkdir -p sdk
mkdir -p forensicsuite_sdk.egg-info

# 2. Vytvorenie setup.py
cat > setup.py << 'SETUP_PY'
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="forensicsuite-sdk",
    version="1.1.0",
    author="ForensicSuite Team",
    description="Modulárna analytická platforma pre softvérové projekty – SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/forensicsuite",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Security",
    ],
    python_requires=">=3.9",
    install_requires=[
        # Žiadne externé závislosti – všetko je v štandardnej knižnici
    ],
    entry_points={
        "console_scripts": [
            "forensicsuite=cli.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
SETUP_PY

echo "[OK] setup.py"

# 3. Vytvorenie pyproject.toml
cat > pyproject.toml << 'TOML_EOF'
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "forensicsuite-sdk"
version = "1.1.0"
description = "Modulárna analytická platforma pre softvérové projekty – SDK"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}
authors = [
    {name = "ForensicSuite Team", email = "team@forensicsuite.dev"}
]
classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]

[tool.setuptools]
packages = ["core", "plugins", "scoring", "reports", "cli", "server", "sdk"]

[tool.setuptools.package-data]
"*" = ["*.yaml", "*.yml", "*.md", "*.html"]
TOML_EOF

echo "[OK] pyproject.toml"

# 4. Vytvorenie MANIFEST.in
cat > MANIFEST.in << 'MANIFEST_EOF'
include README.md
include LICENSE
include config/*.yaml
include dashboard/*.html
recursive-include docs *.md
MANIFEST_EOF

echo "[OK] MANIFEST.in"

# 5. Vytvorenie sdk/__init__.py
cat > sdk/__init__.py << 'INIT_EOF'
"""
ForensicSuite SDK – programové použitie platformy.
"""
from sdk.client import ForensicSuiteClient

__all__ = ["ForensicSuiteClient"]
__version__ = "1.1.0"
INIT_EOF

echo "[OK] sdk/__init__.py"

# 6. Vytvorenie sdk/client.py
cat > sdk/client.py << 'CLIENT_EOF'
import os
from typing import Any, Dict, List, Optional

from core.config_loader import load_config
from core.engine import ForensicEngine


class ForensicSuiteClient:
    """
    Jednoduchý klient pre programové použitie ForensicSuite.
    
    Príklad:
        from forensicsuite_sdk import ForensicSuiteClient
        
        client = ForensicSuiteClient()
        result = client.scan("/path/to/project")
        print(result["scores"])
    """

    def __init__(self, config_path: Optional[str] = None, history_enabled: bool = True):
        """
        Inicializuje klienta.
        
        Args:
            config_path: Cesta ku konfiguračnému súboru (YAML/JSON).
            history_enabled: Či sa má ukladať história skenov.
        """
        self.config = load_config(config_path)
        self.history_enabled = history_enabled
        self.engine = ForensicEngine(
            config=self.config,
            history_enabled=history_enabled,
        )

    def scan(self, project_path: str, save_history: bool = True) -> Dict[str, Any]:
        """
        Spustí sken projektu a vráti výsledok.
        
        Args:
            project_path: Cesta k projektu.
            save_history: Či sa má sken uložiť do histórie.
            
        Returns:
            Kompletný výsledok skenu.
        """
        return self.engine.run(project_path, save_history=save_history)

    def scan_and_report(
        self,
        project_path: str,
        output_dir: str = "forensicsuite_report",
        formats: Optional[List[str]] = None,
        save_history: bool = True,
    ) -> Dict[str, Any]:
        """
        Spustí sken a vygeneruje reporty.
        
        Args:
            project_path: Cesta k projektu.
            output_dir: Výstupný priečinok pre reporty.
            formats: Zoznam formátov (json, markdown, html).
            save_history: Či sa má sken uložiť do histórie.
            
        Returns:
            Kompletný výsledok skenu.
        """
        if formats is None:
            formats = ["json", "markdown", "html"]

        result = self.scan(project_path, save_history=save_history)

        os.makedirs(output_dir, exist_ok=True)

        from reports import json_report, markdown_report, html_report

        fmt_map = {
            "json": json_report,
            "markdown": markdown_report,
            "html": html_report,
        }

        for fmt in formats:
            if fmt in fmt_map:
                out_path = os.path.join(output_dir, f"report.{fmt}")
                fmt_map[fmt].generate(result, out_path)

        return result

    def get_scores(self, project_path: str, save_history: bool = False) -> Dict[str, Any]:
        """
        Vráti iba skóre (rýchla verzia bez reportov).
        
        Args:
            project_path: Cesta k projektu.
            save_history: Či sa má sken uložiť do histórie.
            
        Returns:
            Slovník so skóre.
        """
        result = self.scan(project_path, save_history=save_history)
        return result.get("scores", {})

    def get_history(self, project_path: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Vráti históriu skenov pre daný projekt.
        
        Args:
            project_path: Cesta k projektu (voliteľné).
            limit: Maximálny počet záznamov.
            
        Returns:
            Zoznam historických záznamov.
        """
        if not self.history_enabled:
            return []
        return self.engine.get_history(project_path, limit)

    def get_trend(self, project_path: str, metric: str = "maintainability") -> List[Dict[str, Any]]:
        """
        Vráti trend pre danú metriku.
        
        Args:
            project_path: Cesta k projektu.
            metric: Názov metriky (maintainability, architecture, security).
            
        Returns:
            Zoznam bodov trendu.
        """
        if not self.history_enabled:
            return []
        return self.engine.get_trend(project_path, metric)

    def get_stats(self) -> Dict[str, Any]:
        """
        Vráti štatistiky z histórie.
        
        Returns:
            Slovník so štatistikami.
        """
        if not self.history_enabled:
            return {}
        return self.engine.get_stats()
CLIENT_EOF

echo "[OK] sdk/client.py"

# 7. Vytvorenie LICENSE
cat > LICENSE << 'LICENSE_EOF'
MIT License

Copyright (c) 2026 ForensicSuite Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
LICENSE_EOF

echo "[OK] LICENSE"

# 8. Pridanie testu SDK do tests/test_smoke.py
cat > tests/test_smoke.py << 'TEST_EOF'
import json
import os
import sys
import tempfile

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.engine import ForensicEngine
from core.finding import Finding, Severity, aggregate_findings
from core.history import HistoryManager
from core.tool_runner import ToolRunner


def test_engine_runs_on_self():
    engine = ForensicEngine(history_enabled=False)
    result = engine.run(_PROJECT_ROOT)

    assert result["file_count"] > 0
    assert "filesystem" in result["plugins"]
    assert "python" in result["plugins"]
    assert "javascript" in result["plugins"]
    assert "go" in result["plugins"]
    assert "version" in result
    assert result["version"] == "1.1.0"
    print("OK: smoke test prešiel")


def test_finding_structure():
    finding = Finding(
        plugin="test",
        severity=Severity.CRITICAL,
        message="Test",
        location="test.py:1",
        confidence=0.9,
    )
    assert finding.plugin == "test"
    assert finding.severity == Severity.CRITICAL
    assert finding.confidence == 0.9

    d = finding.to_dict()
    assert d["severity"] == "CRITICAL"
    assert d["confidence"] == 0.9

    f2 = Finding.from_dict(d)
    assert f2.plugin == "test"
    assert f2.severity == Severity.CRITICAL
    print("OK: Finding štruktúra funguje")


def test_aggregate_findings():
    findings = [
        Finding("a", Severity.CRITICAL, "x"),
        Finding("a", Severity.HIGH, "y"),
        Finding("b", Severity.LOW, "z"),
    ]
    agg = aggregate_findings(findings)
    assert agg["total"] == 3
    assert agg["CRITICAL"] == 1
    assert agg["HIGH"] == 1
    assert agg["LOW"] == 1
    assert agg["by_plugin"]["a"] == 2
    assert agg["by_plugin"]["b"] == 1
    print("OK: agregácia funguje")


def test_tool_runner():
    runner = ToolRunner(timeout=5)
    assert runner.check_installed("ls") is True
    rc, out, err = runner.run(["echo", "hello"])
    assert rc == 0
    assert "hello" in out
    print("OK: ToolRunner funguje")


def test_config_loading():
    from core.config_loader import load_config
    config = load_config()
    assert "exclude_dirs" in config
    assert "scoring_weights" in config
    print("OK: config loader prešiel")


def test_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        history = HistoryManager(db_path)

        test_result = {
            "project_path": "/test",
            "file_count": 10,
            "scores": {"maintainability": {"score": 85}},
            "findings": [{"plugin": "test", "severity": "INFO", "message": "test"}],
            "plugins": {"test": {"status": "ok"}},
            "version": "1.1.0",
        }
        scan_id = history.save_scan(test_result)
        assert scan_id > 0

        history_list = history.get_history("/test", limit=10)
        assert len(history_list) >= 1
        assert history_list[0]["scores"]["maintainability"]["score"] == 85

        trend = history.get_trend("/test", "maintainability")
        assert len(trend) >= 1
        assert trend[0]["score"] == 85

        stats = history.get_stats()
        assert stats["total_scans"] >= 1
        print("OK: História funguje")


def test_json_serialization():
    engine = ForensicEngine(history_enabled=False)
    result = engine.run(_PROJECT_ROOT)
    try:
        json.dumps(result)
        print("OK: JSON serializácia prešla")
    except TypeError as e:
        assert False, f"JSON serializácia zlyhala: {e}"


def test_sdk():
    """Test SDK klienta."""
    from sdk.client import ForensicSuiteClient

    client = ForensicSuiteClient(history_enabled=False)
    result = client.scan(_PROJECT_ROOT)
    assert "scores" in result
    assert "maintainability" in result["scores"]

    scores = client.get_scores(_PROJECT_ROOT)
    assert "maintainability" in scores

    print("OK: SDK funguje")


if __name__ == "__main__":
    test_engine_runs_on_self()
    test_finding_structure()
    test_aggregate_findings()
    test_tool_runner()
    test_config_loading()
    test_history()
    test_json_serialization()
    test_sdk()
    print("\n=== VŠETKY TESTY PREŠLI ===")
TEST_EOF

echo "[OK] tests/test_smoke.py – pridaný test SDK"

# 9. Spustenie testov
echo ""
echo "=== SPÚŠŤAM TESTY ==="
python3 tests/test_smoke.py

# 10. Inštalácia SDK v editable režime (voliteľné)
echo ""
echo "=== INŠTALÁCIA SDK (editable mode) ==="
pip install -e . --quiet 2>/dev/null || echo "   ⚠️ pip nie je dostupný, preskakujem inštaláciu"

echo ""
echo "=== SDK HOTOVO ==="
echo "Použitie SDK:"
echo "  from sdk.client import ForensicSuiteClient"
echo "  client = ForensicSuiteClient()"
echo "  result = client.scan('/cesta/k/projektu')"
echo ""
echo "Inštalácia balíka:"
echo "  pip install ."
echo "  # alebo"
echo "  pip install -e .  # pre vývoj"
echo ""
echo "Publikácia na PyPI:"
echo "  python -m build"
echo "  twine upload dist/*"

