from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass
class CheckResult:
    check_id: str
    check_name: str
    passed: bool
    exempted: bool = False
    exemption_reason: str = ""
    findings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    skipped: bool = False
    skipped_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "check_name": self.check_name,
            "passed": self.passed,
            "exempted": self.exempted,
            "exemption_reason": self.exemption_reason,
            "skipped": self.skipped,
            "skipped_reason": self.skipped_reason,
            "findings": self.findings,
            "details": self.details,
        }


@dataclass
class AcceptanceReport:
    passed: bool
    results: list[CheckResult]

    @property
    def has_failures(self) -> bool:
        return any(not r.passed and not r.skipped and not r.exempted for r in self.results)

    @property
    def has_skipped(self) -> bool:
        return any(r.skipped and not r.exempted for r in self.results)

    @property
    def status_summary(self) -> str:
        if self.has_failures:
            return "FAIL"
        if self.has_skipped:
            return "INCOMPLETE (SKIPPED)"
        return "PASS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "status_summary": self.status_summary,
            "has_failures": self.has_failures,
            "has_skipped": self.has_skipped,
            "results": [r.to_dict() for r in self.results],
        }


def is_exempted(check_id: str, pr_labels: Sequence[str]) -> tuple[bool, str]:
    labels = {label.strip() for label in pr_labels if label.strip()}
    if "policy-exempt:mechanical-acceptance" in labels:
        return True, "policy-exempt:mechanical-acceptance"
    specific_label = f"policy-exempt:{check_id.replace('_', '-')}"
    if specific_label in labels:
        return True, specific_label
    return False, ""
