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
