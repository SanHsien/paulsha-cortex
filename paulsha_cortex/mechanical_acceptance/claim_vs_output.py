from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence
from .models import CheckResult, is_exempted


def check_claim_vs_output(
    claimed_count: int | None = None,
    claimed_fixed: bool | None = None,
    claimed_params: Mapping[str, Any] | None = None,
    canonical_params: Mapping[str, Any] | None = None,
    rerun_fn: Callable[[Mapping[str, Any]], int | Sequence[Any]] | None = None,
    residual_findings: Sequence[str] | None = None,
    pr_labels: Sequence[str] = (),
) -> CheckResult:
    """第 1 項：自我宣稱 vs 產出比對。

    重跑時強制使用 canonical_params（不得採信 claimed_params）。
    """
    check_id = "claim_vs_output"
    check_name = "自我宣稱 vs 產出比對"
    exempt, reason = is_exempted(check_id, pr_labels)

    findings: list[str] = []
    details: dict[str, Any] = {}

    has_input = any(
        x is not None
        for x in (
            claimed_count,
            claimed_fixed,
            claimed_params,
            canonical_params,
            rerun_fn,
            residual_findings,
        )
    )

    if not has_input:
        return CheckResult(
            check_id=check_id,
            check_name=check_name,
            passed=exempt,
            exempted=exempt,
            exemption_reason=reason if exempt else "",
            skipped=not exempt,
            skipped_reason="缺少自我宣稱與產出比對 context (claimed_params/canonical_params/rerun_fn/residual_findings)",
            findings=findings,
            details=details,
        )

    # 1. 檢查參數是否遭篡改（例如 #262 實例：subagent 修改 pr-body "Refs" -> "Fixes" 以利過關）
    if claimed_params is not None and canonical_params is not None:
        tampered_keys = []
        for k, v in canonical_params.items():
            if k in claimed_params and claimed_params[k] != v:
                tampered_keys.append(f"{k} (宣稱 '{claimed_params[k]}' vs 規範 '{v}')")
        if tampered_keys:
            findings.append(f"宣稱驗收參數與規範不符（疑似自行修改輸入以通過 gate）: {', '.join(tampered_keys)}")
            details["tampered_params"] = tampered_keys

    # 2. 獨立重跑驗證（重跑驗證端必須使用 canonical_params）
    if rerun_fn is not None:
        params_to_use = canonical_params if canonical_params is not None else (claimed_params or {})
        res = rerun_fn(params_to_use)
        if isinstance(res, int):
            if res > 0:
                findings.append(f"獨立重跑驗證發現 {res} 處殘留問題 (宣稱已修復)")
                details["rerun_residual_count"] = res
        elif isinstance(res, (list, tuple)):
            if len(res) > 0:
                findings.append(f"獨立重跑驗證發現 {len(res)} 處殘留問題: {list(res)}")
                details["rerun_residual_findings"] = list(res)

    elif residual_findings:
        findings.append(f"產出比對發現 {len(residual_findings)} 處殘留問題: {list(residual_findings)}")
        details["residual_findings"] = list(residual_findings)

    if claimed_count is not None and rerun_fn is None:
        actual_count = len(residual_findings or [])
        if claimed_count != actual_count:
            findings.append(f"宣稱數量 ({claimed_count}) 與實際殘留數量 ({actual_count}) 不符")

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
