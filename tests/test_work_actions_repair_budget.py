"""#218: work-item 級 repair budget 與 circuit breaker。

補齊 test_delivery_orchestrator.py／test_work_actions.py 涵蓋不到的兩塊：
red band 透過完整 `_ship_action` 路徑的防禦性拒絕（AC1），以及 repair budget
判定只靠 session count／elapsed time、不依賴任何 provider token 用量資訊的
fail-closed 不變量（AC4）。
"""

from __future__ import annotations

import inspect
import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from paulsha_cortex.coordinator import work_actions
from paulsha_cortex.coordinator.delivery import (
    REVIEW_TIMEOUT_SECONDS,
    ReviewLoop,
    ShipOrchestrator,
)
from paulsha_cortex.coordinator.registry import JobRegistry


def _init_repo(root: Path, repo: str = "acme/demo") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    remote = subprocess.run(
        ["git", "-C", str(root), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if remote.returncode != 0:
        subprocess.run(
            ["git", "-C", str(root), "remote", "add", "origin", f"git@github.com:{repo}.git"],
            check=True,
        )
    return root


def _snapshot(path: Path) -> Path:
    _init_repo(path.parent)
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
                        "work_id": "demo",
                        "mapped_issues": [12],
                        "mapped_prs": [8],
                        "mapped_openspec": ["demo"],
                        "mapped_todo_paths": ["docs/todo.md"],
                        "confirmed_todo": True,
                        "auto_label": True,
                        "source_revisions": ["issue:12@open", "openspec:demo@1"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_ship_action_defensively_rejects_red_band_before_any_ship_state(
    tmp_path: Path,
) -> None:
    """#218 AC1：red 依 #208 判定門檻不得進入 ship 的 repair budget。

    #223 的路由本應在更早階段攔截 red work item；這裡驗證即使一個 red-band
    的 WorkflowRun 仍走到 ship action，也會在建立任何 ship-phase 狀態之前
    fail closed（防禦性拒絕，不是 red 自己另有一組預算）。
    """

    snapshot = _snapshot(tmp_path / "snapshot.json")
    state = tmp_path / "runs.json"
    registry = JobRegistry(state_path=state.parent / "jobs.json")
    started = work_actions.execute_work_action(
        args={"action": "start", "repo": "acme/demo", "work_id": "demo"},
        requested_by="operator",
        snapshot_path=snapshot,
        state_path=state,
        now=lambda: 200,
        workflow_registry=registry,
    )
    run_id = started["result"]["run"]["run_id"]
    registry._manager_update_workflow_run(run_id, sizing_score=7, sizing_band="red")

    with pytest.raises(ValueError, match="red band"):
        work_actions.execute_work_action(
            args={
                "action": "ship",
                "repo": "acme/demo",
                "work_id": "demo",
                "repo_root": str(tmp_path),
                "pr_number": 8,
                "change": "demo",
                "todo_paths": ["docs/todo.md"],
            },
            requested_by="operator",
            snapshot_path=snapshot,
            state_path=state,
            now=lambda: 210,
            workflow_registry=registry,
        )

    if state.is_file():
        payload = json.loads(state.read_text(encoding="utf-8"))
        row = payload["runs"].get(run_id, {})
        assert "ship" not in row


def test_repair_budget_gates_on_round_count_and_elapsed_time_only() -> None:
    """#218 AC4：取不到 provider token 數時，以 session count + elapsed time fail closed。

    這條迴圈自始就沒有任何「provider token 用量」參數可讀——signature 上完全
    不存在，budget 判定結構上只能靠 fix_rounds（session count）與
    now_epoch/REVIEW_TIMEOUT_SECONDS（elapsed time）兩者。
    """

    review_params = set(inspect.signature(ReviewLoop.record_review).parameters)
    merge_params = set(inspect.signature(ShipOrchestrator.merge_if_ready).parameters)
    token_like = {
        name for name in review_params | merge_params if "token" in name.lower()
    }
    assert not token_like

    loop = ReviewLoop.start(head="a" * 40, now_epoch=0, max_fix_rounds=1).mark_requested(
        head="a" * 40, now_epoch=0
    )

    # Session count（fix_rounds）已達 band 預算：純靠回合數即 fail closed。
    exhausted = replace(loop, fix_rounds=1)
    decision = exhausted.record_review(
        head="a" * 40, now_epoch=10, finding_count=1, review_id=1, submitted_at_epoch=10
    )
    assert decision.action == "needs_human"
    assert decision.reason == "copilot-finding-budget-exhausted"

    # Elapsed time 超過 REVIEW_TIMEOUT_SECONDS：純靠牆鐘時間即 fail closed。
    timed_out = loop.record_review(
        head="a" * 40,
        now_epoch=REVIEW_TIMEOUT_SECONDS + 1,
        finding_count=0,
        review_id=1,
        submitted_at_epoch=REVIEW_TIMEOUT_SECONDS + 1,
    )
    assert timed_out.action == "needs_human"
    assert timed_out.reason == "copilot-review-timeout"


def test_semantic_reclaim_budget_forces_needs_human_and_never_creates_v4(tmp_path):
    """#218 AC2（design #208 E）：同一 work item 累積 3 個 superseded 世代後，
    語意 re-claim 熔斷為 needs_human，不得自動建立 v4；計數跨 run_id，
    不受 active dict 換代歸零影響。"""
    from paulsha_cortex.coordinator import work_actions
    from paulsha_cortex.coordinator.registry import JobRegistry
    from paulsha_cortex.coordinator.workflow import WorkflowStep

    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    snapshot = _snapshot(tmp_path / "snapshot.json")
    step = WorkflowStep(
        phase="claim", persona="manager", card="workflow-claim",
        executor=None, model=None, domain=None, inputs=(), outputs=(),
        gate_result="pending",
    )
    # v1..v3：同 (repo, work_id) 連建三代，前兩代自動被 supersede，最後一代手動終結。
    for gen in range(3):
        registry._manager_create_workflow_run(
            repo="acme/demo", work_id="demo",
            claim_key=f"claim:v1:{str(gen) * 64}",
            source_revision=f"rev-{gen}",
            workspace_root="/tmp/workspace", combo="feature-oneshot",
            current_phase="claim", steps=(step,),
            issue_refs=("acme/demo#12",),
        )
    runs = registry.list_workflow_runs()
    last_ongoing = [r for r in runs if r.status == "ongoing"]
    assert len(last_ongoing) == 1
    registry._manager_abandon_workflow_run(
        last_ongoing[0].run_id, evidence_ref="abandon:test-semantic-reclaim"
    )
    assert (
        len([r for r in registry.list_workflow_runs() if r.status == "superseded"]) >= 3
    )

    def _never_start(authority, claim_key, reason):
        raise AssertionError("semantic re-claim 熔斷後不得建立 v4 run")

    outcome = work_actions.execute_work_action(
        args={"action": "start", "repo": "acme/demo", "work_id": "demo", "actor": "operator"},
        requested_by="operator",
        now=lambda: 150.0,
        snapshot_path=snapshot,
        state_path=tmp_path / "journal.jsonl",
        workflow_registry=registry,
        workflow_starter=_never_start,
    )
    result = outcome["result"]
    assert result["action"] == "needs_human"
    assert result["reason"] == "semantic-reclaim-budget-exhausted"
    assert result["superseded_generations"] >= 3
