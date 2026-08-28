from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from paulsha_cortex.mechanical_acceptance import run_acceptance_checks
from . import COMMANDS, PorcelainCommand, register


def register_commands() -> None:
    if "mechanical-acceptance" in COMMANDS:
        return
    register(
        PorcelainCommand(
            name="mechanical-acceptance",
            help="對 agent/subagent 產出執行零 model session 確定性機械驗收",
            run=main,
        )
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cortex mechanical-acceptance",
        description="執行六項零 model session 的確定性收尾機械驗收檢查",
    )
    parser.add_argument("--json", action="store_true", help="輸出 JSON 格式報告")
    parser.add_argument("--input-file", help="讀取 JSON 格式 context input file")
    parser.add_argument("--text-file", help="讀取待檢測的 Markdown/文字檔案")
    parser.add_argument("--pr", help="指定 PR 編號（將自動使用 gh CLI 抓取 PR body/labels/commits 與 Issue 狀態）")
    parser.add_argument("--unresolved-issues", help="以逗號分隔的未解決 Issue 編號（如 277,281）")
    parser.add_argument("--repo-root", help="專案根目錄路徑（用於事實新鮮度核對）")
    parser.add_argument("--pr-labels", help="以逗號分隔的 PR labels（用於白名單豁免）")
    return parser


def main(argv: Sequence[str] | None = None, gh_runner: Any = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    context: dict[str, Any] = {}
    if args.input_file:
        try:
            with open(args.input_file, "r", encoding="utf-8") as f:
                context = json.load(f)
        except Exception as exc:
            sys.stderr.write(f"error: failed to read input file '{args.input_file}': {exc}\n")
            return 1

    if args.pr:
        from paulsha_cortex.mechanical_acceptance import collect_pr_context

        kwargs: dict[str, Any] = {}
        if gh_runner is not None:
            kwargs["gh_runner"] = gh_runner
        if args.repo_root:
            kwargs["repo_root"] = args.repo_root
        pr_context = collect_pr_context(args.pr, **kwargs)
        for k, v in pr_context.items():
            if k not in context or context[k] is None:
                context[k] = v

    if args.text_file:
        try:
            text_content = Path(args.text_file).read_text(encoding="utf-8")
            context["text_content"] = text_content
            if "pr_body" not in context:
                context["pr_body"] = text_content
        except Exception as exc:
            sys.stderr.write(f"error: failed to read text file '{args.text_file}': {exc}\n")
            return 1

    if args.unresolved_issues:
        issues = []
        for raw in args.unresolved_issues.split(","):
            raw_clean = raw.strip().lstrip("#")
            if raw_clean.isdigit():
                issues.append(int(raw_clean))
        context["unresolved_issues"] = issues

    if args.repo_root:
        context["repo_root"] = args.repo_root

    if args.pr_labels:
        labels = [l.strip() for l in args.pr_labels.split(",") if l.strip()]
        context["pr_labels"] = labels

    report = run_acceptance_checks(context)

    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n")
    else:
        status_str = report.status_summary
        sys.stdout.write(f"Mechanical Acceptance Status: {status_str}\n")
        for res in report.results:
            if res.exempted:
                res_str = "EXEMPTED"
                info_str = f" (EXEMPTED: {res.exemption_reason})"
            elif res.skipped:
                res_str = "SKIPPED"
                info_str = f" (缺少必要 context: {res.skipped_reason})"
            elif res.passed:
                res_str = "PASS"
                info_str = ""
            else:
                res_str = "FAIL"
                info_str = ""

            sys.stdout.write(f"- [{res_str}] {res.check_name} ({res.check_id}){info_str}\n")
            for finding in res.findings:
                sys.stdout.write(f"    * {finding}\n")

    if report.passed:
        return 0
    elif report.has_failures:
        return 1
    else:
        return 2
