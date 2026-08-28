"""#208 收口 wiring 2／5 的持久化欄位骨架：``WorkflowRun.plan_review_passed`` 與
``WorkflowRun.frozen_readiness``。

四點同步規則（field／__post_init__ 驗證／to_dict／from_dict）＋
registry create/update 參數＋providers allowlist 皆須到位，否則欄位在
JobRegistry 重新載入（新 process／daemon 重啟）後會靜默丟失，讓 wiring 2／5
表面上測試通過、實際上跨 process 不持久。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from paulsha_cortex.coordinator.registry import JobRegistry
from paulsha_cortex.coordinator.workflow import WorkflowStep


def _step() -> WorkflowStep:
    return WorkflowStep(
        phase="plan", persona="planner", card="writing-plans", executor=None, model=None,
        domain=None, inputs=(), outputs=(), gate_result="pending",
    )


def _frozen_readiness(base_sha: str = "a" * 40) -> dict:
    return {
        "schema": "pre-claim-readiness-frozen-set/v1",
        "repo": "acme/demo",
        "work_id": "demo",
        "base_sha": base_sha,
        "planning_authority_hashes": ["b" * 64],
        "monitor_snapshot_revision": "snap-1",
        "issue_ref": "acme/demo#1",
        "executor_identity": "copilot:gpt",
        "frozen_at_epoch": 1_000.0,
        "live_probe_ttl_cached": False,
    }


def test_defaults_are_false_and_none(tmp_path: Path) -> None:
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    run = registry._manager_create_workflow_run(
        work_id="demo", repo="acme/demo", claim_key="claim:v1:" + "1" * 64,
        source_revision="2" * 64, workspace_root="/tmp/workspace", combo="feature-oneshot",
        current_phase="plan", steps=(_step(),), gate_status="running",
    )
    assert run.plan_review_passed is False
    assert run.frozen_readiness is None
    assert run.to_dict()["plan_review_passed"] is False
    assert run.to_dict()["frozen_readiness"] is None


def test_create_accepts_explicit_values(tmp_path: Path) -> None:
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    frozen = _frozen_readiness()
    run = registry._manager_create_workflow_run(
        work_id="demo", repo="acme/demo", claim_key="claim:v1:" + "1" * 64,
        source_revision="2" * 64, workspace_root="/tmp/workspace", combo="feature-oneshot",
        current_phase="plan", steps=(_step(),), gate_status="running",
        plan_review_passed=True, frozen_readiness=frozen,
    )
    assert run.plan_review_passed is True
    assert run.frozen_readiness == frozen


def test_update_writes_plan_review_passed_and_frozen_readiness_independently(
    tmp_path: Path,
) -> None:
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    run = registry._manager_create_workflow_run(
        work_id="demo", repo="acme/demo", claim_key="claim:v1:" + "1" * 64,
        source_revision="2" * 64, workspace_root="/tmp/workspace", combo="feature-oneshot",
        current_phase="plan", steps=(_step(),), gate_status="running",
    )
    after_freeze = registry._manager_update_workflow_run(
        run.run_id, frozen_readiness=_frozen_readiness()
    )
    assert after_freeze.plan_review_passed is False
    assert after_freeze.frozen_readiness == _frozen_readiness()

    after_gate = registry._manager_update_workflow_run(run.run_id, plan_review_passed=True)
    # 更新 plan_review_passed 不應動到已凍結的 frozen_readiness（各自獨立的
    # None-代表-不變 sentinel 語意，比照既有欄位如 candidate_head 的既有慣例）。
    assert after_gate.plan_review_passed is True
    assert after_gate.frozen_readiness == _frozen_readiness()


def test_frozen_readiness_requires_a_valid_base_sha(tmp_path: Path) -> None:
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    with pytest.raises(ValueError, match="frozen_readiness base_sha"):
        registry._manager_create_workflow_run(
            work_id="demo", repo="acme/demo", claim_key="claim:v1:" + "1" * 64,
            source_revision="2" * 64, workspace_root="/tmp/workspace", combo="feature-oneshot",
            current_phase="plan", steps=(_step(),), gate_status="running",
            frozen_readiness={"base_sha": "not-a-sha"},
        )


def test_plan_review_passed_must_be_boolean(tmp_path: Path) -> None:
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    with pytest.raises(ValueError, match="plan_review_passed"):
        registry._manager_create_workflow_run(
            work_id="demo", repo="acme/demo", claim_key="claim:v1:" + "1" * 64,
            source_revision="2" * 64, workspace_root="/tmp/workspace", combo="feature-oneshot",
            current_phase="plan", steps=(_step(),), gate_status="running",
            plan_review_passed="yes",  # type: ignore[arg-type]
        )


def test_round_trips_through_registry_reload_from_disk(tmp_path: Path) -> None:
    """跨 process／daemon 重啟的持久化保證：新開一個 JobRegistry 讀同一份
    state 檔，欄位必須原樣還原——這是 to_dict／from_dict 四點同步真正要保護
    的情境（純記憶體內操作測不出這個缺口）。
    """

    state_path = tmp_path / "jobs.json"
    registry = JobRegistry(state_path=state_path)
    frozen = _frozen_readiness()
    run = registry._manager_create_workflow_run(
        work_id="demo", repo="acme/demo", claim_key="claim:v1:" + "1" * 64,
        source_revision="2" * 64, workspace_root="/tmp/workspace", combo="feature-oneshot",
        current_phase="plan", steps=(_step(),), gate_status="running",
        plan_review_passed=True, frozen_readiness=frozen,
    )

    reloaded_registry = JobRegistry(state_path=state_path)
    reloaded = reloaded_registry.get_workflow_run(run.run_id)
    assert reloaded.plan_review_passed is True
    assert reloaded.frozen_readiness == frozen
