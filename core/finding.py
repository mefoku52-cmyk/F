from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(Enum):
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5

    def __str__(self) -> str:
        return self.name

    @classmethod
    def from_string(cls, value: str) -> "Severity":
        try:
            return cls[value.upper()]
        except KeyError:
            return Severity.INFO


@dataclass
class Finding:
    plugin: str
    severity: Severity
    message: str
    location: Optional[str] = None
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin": self.plugin,
            "severity": str(self.severity),
            "severity_value": self.severity.value,
            "message": self.message,
            "location": self.location,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Finding":
        severity = Severity.from_string(data.get("severity", "INFO"))
        return cls(
            plugin=data["plugin"],
            severity=severity,
            message=data["message"],
            location=data.get("location"),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
        )


def aggregate_findings(findings: List[Finding]) -> Dict[str, Any]:
    result = {s.name: 0 for s in Severity}
    result["total"] = 0
    result["by_plugin"] = {}
    for finding in findings:
        result["total"] += 1
        result[finding.severity.name] += 1
        if finding.plugin not in result["by_plugin"]:
            result["by_plugin"][finding.plugin] = 0
        result["by_plugin"][finding.plugin] += 1
    return result


def filter_findings(findings: List[Finding], min_severity: Severity = Severity.MEDIUM) -> List[Finding]:
    return [f for f in findings if f.severity.value >= min_severity.value]


def sort_findings(findings: List[Finding], by: str = "severity") -> List[Finding]:
    if by == "severity":
        return sorted(findings, key=lambda f: f.severity.value, reverse=True)
    elif by == "confidence":
        return sorted(findings, key=lambda f: f.confidence, reverse=True)
    return findings
