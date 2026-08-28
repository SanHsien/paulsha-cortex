from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

CLOSING_KEYWORDS_RE = re.compile(
    r"\b(closes?|closed|fixes?|fixed|resolves?|resolved)\s+#(\d+)",
    re.IGNORECASE,
)
REFS_RE = re.compile(r"#(\d+)")


def default_gh_runner(args: list[str]) -> str:
    res = subprocess.run(["gh"] + args, capture_output=True, text=True, check=True)
    return res.stdout


def collect_pr_context(
    pr_number: int | str,
    repo_root: str | Path | None = None,
    gh_runner: Callable[[list[str]], str] = default_gh_runner,
) -> dict[str, Any]:
    """使用 gh CLI 自動蒐集 PR 相關的完整 context。"""
    context: dict[str, Any] = {}
    if repo_root is not None:
        context["repo_root"] = str(repo_root)

    try:
        raw_pr_json = gh_runner(["pr", "view", str(pr_number), "--json", "title,body,labels,commits"])
        pr_data = json.loads(raw_pr_json)

        title = pr_data.get("title", "")
        body = pr_data.get("body", "")
        labels_raw = pr_data.get("labels", [])
        commits_raw = pr_data.get("commits", [])

        context["title"] = title
        context["pr_body"] = body
        context["text_content"] = body
        context["pr_labels"] = [l.get("name", "") for l in labels_raw if isinstance(l, dict) and l.get("name")]

        commit_messages: list[str] = []
        for c in commits_raw:
            if isinstance(c, dict):
                msg = c.get("message")
                if not msg:
                    headline = c.get("messageHeadline", "")
                    c_body = c.get("messageBody", "")
                    msg = f"{headline}\n{c_body}".strip()
                if msg:
                    commit_messages.append(msg)
        context["commit_messages"] = commit_messages

        # 蒐集所有在 PR body 與 commit message 提及的 Issue ID
        referenced_issue_nums: set[int] = set()
        for kw, num_str in CLOSING_KEYWORDS_RE.findall(body):
            referenced_issue_nums.add(int(num_str))
        for num_str in REFS_RE.findall(body):
            referenced_issue_nums.add(int(num_str))

        for msg in commit_messages:
            for kw, num_str in CLOSING_KEYWORDS_RE.findall(msg):
                referenced_issue_nums.add(int(num_str))
            for num_str in REFS_RE.findall(msg):
                referenced_issue_nums.add(int(num_str))

        unresolved_issues: list[int] = []
        for issue_num in sorted(referenced_issue_nums):
            try:
                raw_issue_json = gh_runner(["issue", "view", str(issue_num), "--json", "state,number"])
                issue_data = json.loads(raw_issue_json)
                state = issue_data.get("state", "").upper()
                if state != "CLOSED":
                    unresolved_issues.append(issue_num)
            except Exception:
                # 若查詢個別 issue 失敗，保留保守認定
                unresolved_issues.append(issue_num)

        context["unresolved_issues"] = unresolved_issues

    except Exception as exc:
        context["gh_error"] = str(exc)

    return context
