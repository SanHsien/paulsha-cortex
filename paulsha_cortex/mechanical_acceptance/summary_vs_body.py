from __future__ import annotations

import re
from typing import Any, Mapping, Sequence
from .models import CheckResult, is_exempted


def check_summary_vs_body(
    summary_claims: Mapping[str, int] | Sequence[tuple[str, int]] | None = None,
    body_counts: Mapping[str, int] | Sequence[tuple[str, int]] | None = None,
    text_content: str | None = None,
    pr_labels: Sequence[str] = (),
) -> CheckResult:
    """第 3 項：摘要 vs 內文一致性。

    計數類宣稱（「Red 2 張」「修了 3 個缺陷」）與內文實際條目數比對。
    """
    check_id = "summary_vs_body"
    check_name = "摘要 vs 內文一致性"
    exempt, reason = is_exempted(check_id, pr_labels)

    findings: list[str] = []
    details: dict[str, Any] = {}

    claims_dict: dict[str, int] = {}
    body_dict: dict[str, int] = {}

    if summary_claims:
        if isinstance(summary_claims, dict):
            claims_dict.update(summary_claims)
        else:
            claims_dict.update(dict(summary_claims))

    if body_counts:
        if isinstance(body_counts, dict):
            body_dict.update(body_counts)
        else:
            body_dict.update(dict(body_counts))

    if text_content:
        red_claim_match = re.search(r"Red\s*[:：]?\s*(\d+)\s*張?", text_content, re.IGNORECASE)
        if red_claim_match and "Red" not in claims_dict:
            claims_dict["Red"] = int(red_claim_match.group(1))

        if "Red" in claims_dict and "Red" not in body_dict:
            lines = text_content.splitlines()
            body_lines = [l for l in lines if not re.search(r"摘要|summary|背景", l, re.IGNORECASE)]
            red_in_body = sum(1 for l in body_lines if re.search(r"\bRed\b", l, re.IGNORECASE))
            body_dict["Red"] = red_in_body

    mismatches = []
    for category, claimed_num in claims_dict.items():
        if category in body_dict:
            actual_num = body_dict[category]
            if claimed_num != actual_num:
                mismatches.append(
                    f"'{category}' 摘要宣稱 {claimed_num} 項，但內文實際包含 {actual_num} 項"
                )

    if mismatches:
        findings.extend(mismatches)
        details["summary_body_mismatches"] = mismatches

    passed = len(findings) == 0
    return CheckResult(
        check_id=check_id,
        check_name=check_name,
        passed=passed or exempt,
        exempted=exempt,
        exemption_reason=reason if exempt else "",
        findings=findings,
        details=details,
    )
