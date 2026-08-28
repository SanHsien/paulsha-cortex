from __future__ import annotations

import re
from typing import Any, Mapping, Sequence
from .models import CheckResult, is_exempted

NON_TW_TERMS_MAP: Mapping[str, str] = {
    "驗實資料": "驗證資料",
    "蠻力爆炸": "暴力解法/窮舉",
    "信息": "訊息",
    "鏈接": "連結",
    "軟件": "軟體",
    "數據": "資料",
    "服務器": "伺服器",
    "默認": "預設",
    "代碼": "程式碼",
}

SIMPLIFIED_VARIANTS: Mapping[str, str] = {
    "采": "採",
    "国": "國",
    "写": "寫",
    "视": "視",
    "陆": "陸",
    "码": "碼",
    "库": "庫",
    "单": "單",
    "错": "錯",
    "试": "試",
    "验": "驗",
}


def check_language_conventions(
    text_content: str,
    title: str = "",
    repo_name: str = "hamanpaul/paulsha-cortex",
    pr_labels: Sequence[str] = (),
) -> CheckResult:
    """第 5 項：語言規範。

    `hamanpaul/*` repo 的產出掃簡繁混用與非台灣慣用詞。
    """
    check_id = "language_conventions"
    check_name = "語言規範"
    exempt, reason = is_exempted(check_id, pr_labels)

    findings: list[str] = []
    details: dict[str, Any] = {}

    full_text = f"{title}\n{text_content}" if title else text_content
    if not full_text.strip():
        return CheckResult(
            check_id=check_id,
            check_name=check_name,
            passed=exempt,
            exempted=exempt,
            exemption_reason=reason if exempt else "",
            skipped=not exempt,
            skipped_reason="缺少待檢測文字內容 (text_content/title)",
            findings=findings,
            details=details,
        )

    # 1. 簡繁/異體混用檢查 (例如標題用「采」內文用「採」)
    used_simplified: list[str] = []
    for simp_char, trad_char in SIMPLIFIED_VARIANTS.items():
        if simp_char in full_text:
            if trad_char in full_text or (title and simp_char in title):
                used_simplified.append(
                    f"檢出簡體/異體字 '{simp_char}'（與正體字 '{trad_char}' 混用或非 Taiwan 規範字）"
                )

    if used_simplified:
        findings.extend(used_simplified)
        details["simplified_variants"] = used_simplified

    # 2. 非台灣慣用詞檢查 (例如「驗實資料」「蠻力爆炸」「信息」「代碼」)
    used_non_tw: list[str] = []
    for non_tw, suggested in NON_TW_TERMS_MAP.items():
        if non_tw in full_text:
            used_non_tw.append(
                f"檢出非台灣慣用詞 '{non_tw}'（建議改用 '{suggested}'）"
            )

    if used_non_tw:
        findings.extend(used_non_tw)
        details["non_tw_terms"] = used_non_tw

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
