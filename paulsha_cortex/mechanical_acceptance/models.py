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


@dataclass
class AcceptanceReport:
    passed: bool
    results: list[CheckResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "results": [
                {
                    "check_id": r.check_id,
                    "check_name": r.check_name,
                    "passed": r.passed,
                    "exempted": r.exempted,
                    "exemption_reason": r.exemption_reason,
                    "findings": r.findings,
                    "details": r.details,
                }
                for r in self.results
            ],
        }


def is_exempted(check_id: str, pr_labels: Sequence[str]) -> tuple[bool, str]:
    labels = {label.strip() for label in pr_labels if label.strip()}
    if "policy-exempt:mechanical-acceptance" in labels:
        return True, "policy-exempt:mechanical-acceptance"
    specific_label = f"policy-exempt:{check_id.replace('_', '-')}"
    if specific_label in labels:
        return True, specific_label
    return False, ""
