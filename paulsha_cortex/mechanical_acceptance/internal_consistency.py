from __future__ import annotations

from typing import Any, Mapping, Sequence
from .models import CheckResult, is_exempted


def check_internal_consistency(
    rule_bands: Mapping[str, tuple[int, int]] | None = None,
    classified_items: Sequence[Mapping[str, Any]] | None = None,
    test_assertion_audits: Sequence[Mapping[str, Any]] | None = None,
    pr_labels: Sequence[str] = (),
) -> CheckResult:
    """第 2 項：輸出內部一致性。

    1. 比對規則 (rule_bands) 與套用結果 (classified_items) 是否自洽。
    2. 檢查測試斷言強度是否滿足其所宣稱驗證之 Requirement 語意要求。
    """
    check_id = "internal_consistency"
    check_name = "輸出內部一致性"
    exempt, reason = is_exempted(check_id, pr_labels)

    findings: list[str] = []
    details: dict[str, Any] = {}
    has_input = bool((rule_bands and classified_items) or test_assertion_audits)

    if not has_input:
        return CheckResult(
            check_id=check_id,
            check_name=check_name,
            passed=exempt,
            exempted=exempt,
            exemption_reason=reason if exempt else "",
            skipped=not exempt,
            skipped_reason="缺少內部一致性規則 context (rule_bands/classified_items 或 test_assertion_audits)",
            findings=findings,
            details=details,
        )

    # 1. 規則 vs 套用結果自洽性
    if rule_bands and classified_items:
        mismatches = []
        for item in classified_items:
            name = item.get("name", "unnamed")
            score = item.get("score")
            label = item.get("label") or item.get("band")
            if score is None or label is None:
                continue

            expected_band = None
            for band_name, (low, high) in rule_bands.items():
                if low <= score <= high:
                    expected_band = band_name
                    break

            if expected_band and label != expected_band:
                mismatches.append(
                    f"'{name}' 分數 {score} 依規則屬於 '{expected_band}' ({rule_bands[expected_band]}), "
                    f"但標記為 '{label}'"
                )
        if mismatches:
            findings.extend(mismatches)
            details["classification_mismatches"] = mismatches

    # 2. 測試斷言強度與 Requirement 語意比對 (#256 實例)
    if test_assertion_audits:
        weak_assertions = []
        for audit in test_assertion_audits:
            test_name = audit.get("test_name", "unnamed_test")
            spec_ref = audit.get("spec_ref", "unspecified_spec")
            requires_value_check = audit.get("requires_value_check", False)
            has_value_check = audit.get("has_value_check", False)
            has_existence_check_only = audit.get("has_existence_check_only", False)

            if requires_value_check and (has_existence_check_only or not has_value_check):
                weak_assertions.append(
                    f"測試 '{test_name}' 宣稱驗證 '{spec_ref}'（要求數值/語意正確），"
                    f"但斷言僅驗證欄位存在/非空，缺乏語意值比對 (assert equality)"
                )
        if weak_assertions:
            findings.extend(weak_assertions)
            details["weak_test_assertions"] = weak_assertions

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
