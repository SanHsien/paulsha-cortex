from __future__ import annotations

import re
from typing import Any, Sequence
from .models import CheckResult, is_exempted

QUANT_ESTIMATE_RE = re.compile(
    r"(?:總時程|預估耗時|估算|時程|成本|耗時)\s*[:：]?\s*\d+[\s–\-~〜]*\d*\s*(?:個|條|天|工作天|小時|週|周|月|元|USD)",
    re.IGNORECASE,
)

SOURCE_PATTERNS_RE = re.compile(
    r"(?:https?://|Refs\s+#\d+|issue\s+#\d+|依據[：:]|來源[：:]|benchmarks?|formula)",
    re.IGNORECASE,
)


def check_unsubstantiated_quantification(
    text_content: str,
    pr_labels: Sequence[str] = (),
) -> CheckResult:
    """第 6 項：禁止無依據量化。

    工時、成本、時程估算若無可追溯資料來源即視為雜訊。
    """
    check_id = "unsubstantiated_quantification"
    check_name = "禁止無依據量化"
    exempt, reason = is_exempted(check_id, pr_labels)

    findings: list[str] = []
    details: dict[str, Any] = {}

    if not text_content or not text_content.strip():
        return CheckResult(
            check_id=check_id,
            check_name=check_name,
            passed=exempt,
            exempted=exempt,
            exemption_reason=reason if exempt else "",
            skipped=not exempt,
            skipped_reason="缺少待檢測文字內容 (text_content)",
            findings=findings,
            details=details,
        )

    unsubstantiated_estimates = []
    lines = text_content.splitlines()

    for line in lines:
        if QUANT_ESTIMATE_RE.search(line):
            if not SOURCE_PATTERNS_RE.search(line) and not SOURCE_PATTERNS_RE.search(text_content):
                unsubstantiated_estimates.append(
                    f"估算宣稱 '{line.strip()}' 缺乏可追溯資料來源（如 依據: / Issue # / URL / benchmark）"
                )

    if unsubstantiated_estimates:
        findings.extend(unsubstantiated_estimates)
        details["unsubstantiated_estimates"] = unsubstantiated_estimates

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
