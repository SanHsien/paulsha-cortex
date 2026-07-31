"""#135：persona scope 歷史回放。

以近期已合併 PR（main 上的 merge commit）之檔案清單，回放 persona scope 判定，
用以在切換 enforcement shadow → enforce 之前證明零誤殺（R1 / D1）。

角色假設：本 repo 目前所有透過 coordinator 派工並合併進 main 的變更集，
派工角色恆為 `builder`（見 `paulsha_cortex/coordinator/manager.py`：
`job.get("persona")` 缺省即 `"builder"`；CLI `--persona` 亦缺省 `builder`）。
`builder` 的 write_paths 為 `["**"]`（不限範圍），這反映的是「當前實際派工慣例
下，enforce 化不會誤傷既有合併路徑」，而非放寬或迴避檢查——scope 判定本身
（`PersonaGuardrail.evaluate_filesystem`）與 enforce 模式下實際使用的邏輯完全
相同，只是離線地對歷史 diff 重放一次。

若日後 planner / reviewer / manager 角色開始直接產出獨立 PR，須擴充此回放以
涵蓋對應角色歸戶，而不是持續假設 builder。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence

from .contract import PersonaContract
from .guardrail import PersonaGuardrail
from .loader import load_catalog

DEFAULT_REPLAY_ROLE = "builder"
DEFAULT_LIMIT = 30
DEFAULT_REF = "main"


def list_recent_merges(
    repo_root: str | Path, limit: int = DEFAULT_LIMIT, ref: str = DEFAULT_REF
) -> list[tuple[str, str, str]]:
    """列出 `ref` 上最近 `limit` 個 merge commit 的 (merge_sha, parent1, parent2)。

    只保留二親 merge（typical PR merge commit）；非二親（例如 root commit
    誤入 --merges 篩選之外的邊界情況）略過。
    """
    cmd = [
        "git",
        "-C",
        str(repo_root),
        "log",
        "--merges",
        "--first-parent",
        ref,
        "-n",
        str(limit),
        "--format=%H %P",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git log 失敗（fail-closed）: {proc.stderr.strip()}")

    merges: list[tuple[str, str, str]] = []
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        merge_sha, parent1, parent2 = parts[0], parts[1], parts[2]
        merges.append((merge_sha, parent1, parent2))
    return merges


def changed_paths_for_merge(repo_root: str | Path, parent1: str, parent2: str) -> list[str]:
    """PR 實際內容的檔案清單：base(parent1)...head(parent2) 三點差異。"""
    cmd = [
        "git",
        "-C",
        str(repo_root),
        "-c",
        "core.quotepath=false",
        "diff",
        "--name-only",
        f"{parent1}...{parent2}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git diff 失敗（fail-closed）: {proc.stderr.strip()}")
    return [line for line in proc.stdout.splitlines() if line.strip()]


def replay(
    *,
    repo_root: str | Path | None = None,
    limit: int = DEFAULT_LIMIT,
    ref: str = DEFAULT_REF,
    role: str = DEFAULT_REPLAY_ROLE,
    catalog: Mapping[str, PersonaContract] | None = None,
) -> dict[str, object]:
    """回放最近 `limit` 個已合併 PR 的檔案清單，回傳可重跑、結構化的結果。"""
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    resolved_catalog = catalog if catalog is not None else load_catalog()
    rail = PersonaGuardrail(resolved_catalog)

    merges = list_recent_merges(root, limit=limit, ref=ref)

    per_pr: list[dict[str, object]] = []
    total_files = 0
    total_violations: list[dict[str, str]] = []

    for merge_sha, parent1, parent2 in merges:
        paths = changed_paths_for_merge(root, parent1, parent2)
        total_files += len(paths)
        violations: list[dict[str, str]] = []
        for path in paths:
            decision = rail.evaluate_filesystem(role=role, path=path)
            if not decision.allowed:
                violations.append(
                    {"path": path, "rule_id": decision.rule_id, "reason": decision.reason}
                )
        per_pr.append(
            {
                "merge": merge_sha,
                "changed_paths": paths,
                "violations": violations,
            }
        )
        total_violations.extend(violations)

    return {
        "role": role,
        "ref": ref,
        "limit": limit,
        "prs_scanned": len(merges),
        "files_scanned": total_files,
        "false_positives": len(total_violations),
        "results": per_pr,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m paulsha_cortex.persona.replay")
    parser.add_argument("--repo", default=None, help="repo root（預設 cwd）")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--role", default=DEFAULT_REPLAY_ROLE)
    args = parser.parse_args(argv)

    summary = replay(repo_root=args.repo, limit=args.limit, ref=args.ref, role=args.role)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["false_positives"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
