from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Sequence
from .models import CheckResult, is_exempted

CLOSING_KEYWORDS_RE = re.compile(
    r"\b(closes?|closed|fixes?|fixed|resolves?|resolved)\s+#(\d+)",
    re.IGNORECASE,
)


def check_fact_freshness(
    text_content: str = "",
    pr_body: str = "",
    commit_messages: Sequence[str] = (),
    referenced_files: Sequence[str] = (),
    repo_root: str | Path | None = None,
    unresolved_issues: Sequence[int] | None = None,
    unresolved_issues_provided: bool = False,
    pr_labels: Sequence[str] = (),
) -> CheckResult:
    """第 4 項：事實新鮮度。

    1. 產出中的檔名/路徑/設定鍵對 repo 實際狀態核對。
    2. closing keyword 需同時檢查 PR body 與 commit message 兩個來源。
    """
    check_id = "fact_freshness"
    check_name = "事實新鮮度"
    exempt, reason = is_exempted(check_id, pr_labels)

    findings: list[str] = []
    details: dict[str, Any] = {}

    if unresolved_issues is not None:
        unresolved_issues_provided = True
        unresolved_list = list(unresolved_issues)
    else:
        unresolved_list = []

    has_content = bool(text_content or pr_body or commit_messages or referenced_files)
    if not has_content:
        return CheckResult(
            check_id=check_id,
            check_name=check_name,
            passed=exempt,
            exempted=exempt,
            exemption_reason=reason if exempt else "",
            skipped=not exempt,
            skipped_reason="缺少待檢測文字、PR body 或 commit 訊息 context",
            findings=findings,
            details=details,
        )

    # 檢查是否有 closing keywords
    closing_matches = []
    for src_name, text in [("PR body", pr_body), ("text_content", text_content)]:
        if text:
            for kw, num_str in CLOSING_KEYWORDS_RE.findall(text):
                closing_matches.append((src_name, kw, int(num_str)))
    for idx, msg in enumerate(commit_messages):
        if msg:
            for kw, num_str in CLOSING_KEYWORDS_RE.findall(msg):
                closing_matches.append((f"Commit msg #{idx+1}", kw, int(num_str)))

    if closing_matches and not unresolved_issues_provided:
        sample_src, sample_kw, sample_num = closing_matches[0]
        return CheckResult(
            check_id=check_id,
            check_name=check_name,
            passed=exempt,
            exempted=exempt,
            exemption_reason=reason if exempt else "",
            skipped=not exempt,
            skipped_reason=f"檢出 closing keyword '{sample_kw} #{sample_num}' ({sample_src})，但缺少 unresolved_issues 上下文，無法核對 issue 狀態",
            findings=findings,
            details=details,
        )

    root = Path(repo_root) if repo_root is not None else Path.cwd()

    # 1. 檔名/設定檔新鮮度檢查
    obsolete_references = []
    files_to_check = list(referenced_files)
    if text_content:
        for match in re.findall(r"\.[\w\-]+\.(?:yml|yaml|json|toml|py)", text_content):
            if match not in files_to_check:
                files_to_check.append(match)

    for ref in files_to_check:
        if ref == ".paul-project.yml" and not (root / ".paul-project.yml").exists():
            current = ".project-policy.yml" if (root / ".project-policy.yml").exists() else "新版設定檔"
            obsolete_references.append(f"引用過時設定檔 '{ref}'（現已更名為 '{current}'）")
        elif not os.path.isabs(ref) and "/" in ref and not (root / ref).exists():
            obsolete_references.append(f"引用不存在或已移動之檔案/路徑 '{ref}'")

    if obsolete_references:
        findings.extend(obsolete_references)
        details["obsolete_references"] = obsolete_references

    # 2. Closing Keyword (PR body + Commit messages 雙重來源檢查)
    unresolved_set = set(unresolved_list)
    closing_violations = []

    if pr_body:
        for kw, issue_num_str in CLOSING_KEYWORDS_RE.findall(pr_body):
            issue_num = int(issue_num_str)
            if issue_num in unresolved_set:
                closing_violations.append(
                    f"PR body 使用 closing keyword '{kw} #{issue_num}'，但 Issue #{issue_num} 未完全解決（應使用 Refs #{issue_num}）"
                )

    for idx, commit_msg in enumerate(commit_messages):
        for kw, issue_num_str in CLOSING_KEYWORDS_RE.findall(commit_msg):
            issue_num = int(issue_num_str)
            if issue_num in unresolved_set:
                closing_violations.append(
                    f"Commit msg #{idx+1} ('{commit_msg.strip().splitlines()[0]}') 使用 closing keyword '{kw} #{issue_num}'，"
                    f"但 Issue #{issue_num} 未完全解決（此操作會導致 merge 時自動誤關 Issue，應改用 Refs #{issue_num}）"
                )

    if closing_violations:
        findings.extend(closing_violations)
        details["closing_keyword_violations"] = closing_violations

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
