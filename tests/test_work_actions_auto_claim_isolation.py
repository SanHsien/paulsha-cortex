"""#216 迴歸測試：daemon tick 的 auto-claim 掃描逐 authority 隔離。

背景（見 manager.log 現場證據）：`run_auto_claim_scan` 的
``for authority in authorities:`` 迴圈以前完全沒有包住 ``_claim_action`` ->
``workflow_starter`` -> ``resolve_trusted_repo_root`` 這條呼叫鏈；任一
authority 對應的 repo 不在信任清單中，``resolve_trusted_repo_root`` 一
``ValueError`` 就會讓整批 scan 中止，17,013 次同樣錯誤每 4-5 秒重複一次、
持續 22 小時。本檔驗證單一 authority 的 claim 失敗只會產生一筆
``blocked`` 結果，不影響其餘 authority 的處理。
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from paulsha_cortex.coordinator import work_actions
from paulsha_cortex.coordinator.registry import JobRegistry


def _three_authority_snapshot(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": "work-items-snapshot/v1",
                "providers": {
                    "github": {
                        "provider_id": "github",
                        "revision": "gh-1",
                        "last_success_epoch": 100,
                        "degraded": False,
                    }
                },
                "work_items": [
                    {
                        "repo": "acme/demo",
                        "work_id": f"demo-{index}",
                        "mapped_issues": [issue],
                        "mapped_prs": [],
                        "mapped_openspec": [f"demo-{index}"],
                        "mapped_todo_paths": [f"docs/todo-{index}.md"],
                        "confirmed_todo": True,
                        "auto_label": True,
                        "source_revisions": [
                            f"issue:{issue}@open",
                            f"openspec:demo-{index}@1",
                        ],
                    }
                    for index, issue in ((1, 11), (2, 12), (3, 13))
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _labeled_runner(argv, **kwargs):
    return SimpleNamespace(
        returncode=0,
        stdout=json.dumps({"labels": [{"name": "cortex:auto-on-going"}]}),
        stderr="",
    )


def _starter_failing_for(*, registry: JobRegistry, state_path: Path, fail_work_id: str):
    base_starter = work_actions._fallback_workflow_starter(registry, state_path)

    def starter(authority, claim_key, reason):
        if authority.work_id == fail_work_id:
            raise ValueError(
                "trusted repo registry did not resolve exactly one owner/name root"
            )
        return base_starter(authority, claim_key, reason)

    return starter


def test_run_auto_claim_scan_isolates_single_authority_claim_failure(tmp_path: Path) -> None:
    snapshot = _three_authority_snapshot(tmp_path / "snapshot.json")
    state = tmp_path / "runs.json"
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    starter = _starter_failing_for(registry=registry, state_path=state, fail_work_id="demo-2")

    result = work_actions.run_auto_claim_scan(
        snapshot_path=snapshot,
        state_path=state,
        now=lambda: 200,
        runner=_labeled_runner,
        workflow_registry=registry,
        workflow_starter=starter,
    )

    # 整體呼叫不 raise，三個 authority 都有對應結果。
    assert [row["work_id"] for row in result] == ["demo-1", "demo-2", "demo-3"]

    first, middle, last = result
    assert first["action"] == "claim"
    assert last["action"] == "claim"

    # 中間那筆 starter raise ValueError，被轉成結構化 blocked 結果，
    # 不得中止整批掃描。
    assert middle["action"] == "blocked"
    assert middle["reason"] == "repo-root-unresolved"
    assert middle["repo"] == "acme/demo"
    assert "ValueError" in middle["error"]
    assert "trusted repo registry" in middle["error"]
    # 錯誤摘要不得夾帶絕對路徑。
    assert str(tmp_path) not in middle["error"]

    # 另外兩個 authority 確實建立了 workflow run；失敗的那個沒有。
    runs = registry.list_workflow_runs()
    assert {run.work_id for run in runs} == {"demo-1", "demo-3"}
    assert all(run.status == "ongoing" for run in runs)


def test_run_auto_claim_scan_claim_failed_reason_for_generic_starter_error(
    tmp_path: Path,
) -> None:
    """非 resolve_trusted_repo_root 型別的失敗，reason 落在通用的
    ``claim-failed``，仍然是可預期的失敗類型（RuntimeError）而非裸吞。
    """

    snapshot = _three_authority_snapshot(tmp_path / "snapshot.json")
    state = tmp_path / "runs.json"
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    base_starter = work_actions._fallback_workflow_starter(registry, state)

    def starter(authority, claim_key, reason):
        if authority.work_id == "demo-2":
            raise RuntimeError("workspace lock unavailable")
        return base_starter(authority, claim_key, reason)

    result = work_actions.run_auto_claim_scan(
        snapshot_path=snapshot,
        state_path=state,
        now=lambda: 200,
        runner=_labeled_runner,
        workflow_registry=registry,
        workflow_starter=starter,
    )

    middle = result[1]
    assert middle["work_id"] == "demo-2"
    assert middle["action"] == "blocked"
    assert middle["reason"] == "claim-failed"
    assert "RuntimeError" in middle["error"]
    assert [row["work_id"] for row in result] == ["demo-1", "demo-2", "demo-3"]
