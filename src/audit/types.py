"""types — audit data structures."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    OK = "ok"
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class FindingType(str, Enum):
    CLASSIFICATION_CONSISTENCY = "classification_consistency"
    SIGNAL_COVERAGE = "signal_coverage"
    STRUCTURAL_DEFECT = "structural_defect"
    UNCERTAINTY_REACTION = "uncertainty_reaction"   # VSM-005 §5
    PROVIDER_VIOLATION = "provider_violation"


@dataclass
class AuditFinding:
    """A single finding from S3* audit."""

    finding_type: FindingType
    severity: Severity
    message: str
    detail: str = ""
    classification_id: str | None = None  # which classification this concerns


@dataclass
class AuditResult:
    """Result of auditing one or more classifications."""

    findings: list[AuditFinding] = field(default_factory=list)
    passed: bool = True       # no critical findings
    algedonic: bool = False   # should escalate to S5

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def warn_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARN)

    def add(self, finding: AuditFinding):
        self.findings.append(finding)
        if finding.severity == Severity.CRITICAL:
            self.passed = False
            self.algedonic = True
