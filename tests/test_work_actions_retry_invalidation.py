"""#216：retry 分類補齊（authority_restart／review_handoff_failure／
source_owner_repair）與精準 invalidation（retry-build／retry-verify／
retry-review／authority restart）。

驗收條件對應：
- AC1：retry-build 只重跑 builder，invalidate candidate 相依的 verify/review
       （regression：既有 #215 行為，本檔補一條聚焦測試鎖住）
- AC2：retry-verify candidate 不變時只重跑 verification，不重建 candidate
- AC3：retry-review 不重跑 builder；缺 frozen plan 時 pre-dispatch fail
- AC4：source-owner／claim sequencing repair 不觸發 builder
- AC5：authority restart 只 invalidate 依賴已變更 authority hash 的 stage
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from paulsha_cortex.coordinator import work_actions
from paulsha_cortex.coordinator.registry import JobRegistry
from paulsha_cortex.coordinator.workflow import PlanningArtifactAuthority, WorkflowStep


HEAD = "b" * 40
NOW = "2026-07-27T00:00:00+00:00"

_PERSONA_BY_PHASE = {
    "claim": "manager",
    "define": "planner",
    "plan": "planner",
    "build": "builder",
    "verify": "reviewer",
    "review": "reviewer",
    "ship": "manager",
}


def _step(phase: str, card: str, *, gate_result: str = "pending") -> WorkflowStep:
    return WorkflowStep(
        phase=phase,
        persona=_PERSONA_BY_PHASE[phase],
        card=card,
        executor=None,
        model=None,
        domain=None,
        inputs=(),
        outputs=(),
        gate_result=gate_result,
    )


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


def _snapshot(path: Path, *, source_revisions: list[str] | None = None) -> Path:
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
                        "source_revisions": source_revisions
                        or ["issue:12@open", "openspec:demo@1"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _authority(tmp_path: Path, *, source_revisions: list[str] | None = None):
    snapshot = _snapshot(tmp_path / "snapshot.json", source_revisions=source_revisions)
    return work_actions.load_work_authority(
        repo="acme/demo", work_id="demo", snapshot_path=snapshot
    ), snapshot


def _make_run(
    registry: JobRegistry,
    *,
    authority,
    claim_key: str,
    current_phase: str,
    steps: tuple[WorkflowStep, ...],
    candidate_head: str | None = None,
    verified_head: str | None = None,
    facets: tuple[str, ...] = (),
    planning_authority: tuple[PlanningArtifactAuthority, ...] = (),
    source_revision: str | None = None,
):
    return registry._manager_create_workflow_run(
        work_id=authority.work_id,
        repo=authority.repo,
        claim_key=claim_key,
        source_revision=source_revision or work_actions.work_authority_digest(authority),
        workspace_root="/tmp/workspace",
        combo="feature-oneshot",
        current_phase=current_phase,
        steps=steps,
        issue_refs=tuple(f"{authority.repo}#{n}" for n in authority.mapped_issues),
        openspec_refs=authority.mapped_openspec,
        candidate_head=candidate_head,
        verified_head=verified_head,
        facets=facets,
        gate_status="running",
        planning_authority=planning_authority,
    )


def _base_steps(*, verify_result: str, review_result: str) -> tuple[WorkflowStep, ...]:
    return (
        _step("claim", "manager-claim", gate_result="passed"),
        _step("define", "planner-define", gate_result="passed"),
        _step("plan", "planner-plan", gate_result="passed"),
        _step("build", "subagent-build", gate_result="passed"),
        _step("verify", "reviewer-verify", gate_result=verify_result),
        _step("review", "reviewer-review", gate_result=review_result),
        _step("ship", "manager-ship", gate_result="pending"),
    )


# ---------------------------------------------------------------------------
# AC1（regression）：retry-build 只重跑 builder，invalidate verify/review
# ---------------------------------------------------------------------------


def test_retry_build_invalidates_verify_and_review_but_reruns_only_builder(
    tmp_path: Path,
) -> None:
    authority, snapshot = _authority(tmp_path)
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    claim_key = work_actions._expected_claim_key(authority)
    steps = _base_steps(verify_result="passed", review_result="passed")
    run = _make_run(
        registry,
        authority=authority,
        claim_key=claim_key,
        current_phase="review",
        steps=steps,
        candidate_head=HEAD,
        verified_head=HEAD,
        facets=("needs_human",),
    )
    result = work_actions.execute_work_action(
        args={
            "action": "retry-build",
            "repo": "acme/demo",
            "work_id": "demo",
            "issue": 12,
            "actor": "operator",
            "expected_candidate": HEAD,
        },
        requested_by="operator",
        snapshot_path=snapshot,
        state_path=tmp_path / "runs.json",
        workflow_registry=registry,
    )
    updated = result["result"]["run"]
    assert updated["current_phase"] == "build"
    by_phase = {step["phase"]: step for step in updated["steps"]}
    assert by_phase["build"]["gate_result"] == "pending"
    assert by_phase["verify"]["gate_result"] == "pending"
    assert by_phase["review"]["gate_result"] == "pending"
    assert updated["verified_head"] is None
    assert result["result"]["retry_classification"] == "model_repair"
    # #216 追加：分類同步持久化到 WorkflowRun 本身（供 completion draft 讀取）。
    assert updated["retry_classification"] == "model_repair"


# ---------------------------------------------------------------------------
# AC2：retry-verify 候選不變時只重跑 verification，不重建 candidate
# ---------------------------------------------------------------------------


def test_retry_verify_reruns_only_verification_without_rebuilding_candidate(
    tmp_path: Path,
) -> None:
    authority, snapshot = _authority(tmp_path)
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    claim_key = work_actions._expected_claim_key(authority)
    steps = _base_steps(verify_result="needs_human", review_result="pending")
    run = _make_run(
        registry,
        authority=authority,
        claim_key=claim_key,
        current_phase="verify",
        steps=steps,
        candidate_head=HEAD,
        facets=("needs_human",),
    )
    result = work_actions.execute_work_action(
        args={
            "action": "retry-verify",
            "repo": "acme/demo",
            "work_id": "demo",
            "issue": 12,
            "actor": "operator",
            "expected_candidate": HEAD,
        },
        requested_by="operator",
        snapshot_path=snapshot,
        state_path=tmp_path / "runs.json",
        workflow_registry=registry,
    )
    updated = result["result"]["run"]
    assert updated["current_phase"] == "verify"
    by_phase = {step["phase"]: step for step in updated["steps"]}
    # build 完全不動：still "passed"，attempts 未增加
    assert by_phase["build"]["gate_result"] == "passed"
    assert run.attempts.get("build", 0) == updated["attempts"].get("build", 0)
    assert by_phase["verify"]["gate_result"] == "pending"
    assert updated["candidate_head"] == HEAD
    assert "needs_human" not in updated["facets"]
    assert result["result"]["retry_classification"] == "model_repair"
    assert updated["retry_classification"] == "model_repair"


def test_retry_verify_rejects_candidate_mismatch(tmp_path: Path) -> None:
    authority, snapshot = _authority(tmp_path)
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    claim_key = work_actions._expected_claim_key(authority)
    steps = _base_steps(verify_result="needs_human", review_result="pending")
    _make_run(
        registry,
        authority=authority,
        claim_key=claim_key,
        current_phase="verify",
        steps=steps,
        candidate_head=HEAD,
        facets=("needs_human",),
    )
    with pytest.raises(RuntimeError, match="Candidate CAS mismatch"):
        work_actions.execute_work_action(
            args={
                "action": "retry-verify",
                "repo": "acme/demo",
                "work_id": "demo",
                "issue": 12,
                "actor": "operator",
                "expected_candidate": "c" * 40,
            },
            requested_by="operator",
            snapshot_path=snapshot,
            state_path=tmp_path / "runs.json",
            workflow_registry=registry,
        )


def test_retry_verify_rejects_non_verify_phase(tmp_path: Path) -> None:
    authority, snapshot = _authority(tmp_path)
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    claim_key = work_actions._expected_claim_key(authority)
    steps = _base_steps(verify_result="passed", review_result="needs_human")
    _make_run(
        registry,
        authority=authority,
        claim_key=claim_key,
        current_phase="review",
        steps=steps,
        candidate_head=HEAD,
        verified_head=HEAD,
        facets=("needs_human",),
    )
    with pytest.raises(RuntimeError, match="requires verify-phase workflow"):
        work_actions.execute_work_action(
            args={
                "action": "retry-verify",
                "repo": "acme/demo",
                "work_id": "demo",
                "issue": 12,
                "actor": "operator",
                "expected_candidate": HEAD,
            },
            requested_by="operator",
            snapshot_path=snapshot,
            state_path=tmp_path / "runs.json",
            workflow_registry=registry,
        )


# ---------------------------------------------------------------------------
# AC3：retry-review 不重跑 builder；缺 frozen plan 時 pre-dispatch fail
# ---------------------------------------------------------------------------


def test_retry_review_reruns_only_review_without_rebuilding_or_reverifying(
    tmp_path: Path,
) -> None:
    authority, snapshot = _authority(tmp_path)
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    claim_key = work_actions._expected_claim_key(authority)
    steps = _base_steps(verify_result="passed", review_result="needs_human")
    plan_authority = (
        PlanningArtifactAuthority(
            ref="docs/superpowers/plans/demo.md",
            kind="plan",
            work_id="demo",
            baseline_sha256="a" * 64,
        ),
    )
    run = _make_run(
        registry,
        authority=authority,
        claim_key=claim_key,
        current_phase="review",
        steps=steps,
        candidate_head=HEAD,
        verified_head=HEAD,
        facets=("needs_human",),
        planning_authority=plan_authority,
    )
    result = work_actions.execute_work_action(
        args={
            "action": "retry-review",
            "repo": "acme/demo",
            "work_id": "demo",
            "issue": 12,
            "actor": "operator",
            "expected_candidate": HEAD,
        },
        requested_by="operator",
        snapshot_path=snapshot,
        state_path=tmp_path / "runs.json",
        workflow_registry=registry,
    )
    updated = result["result"]["run"]
    assert updated["current_phase"] == "review"
    by_phase = {step["phase"]: step for step in updated["steps"]}
    assert by_phase["build"]["gate_result"] == "passed"
    assert by_phase["verify"]["gate_result"] == "passed"
    assert by_phase["review"]["gate_result"] == "pending"
    assert run.attempts.get("verify", 0) == updated["attempts"].get("verify", 0)
    assert updated["candidate_head"] == HEAD
    assert updated["verified_head"] == HEAD
    assert result["result"]["retry_classification"] == "model_repair"
    assert updated["retry_classification"] == "model_repair"


def test_retry_review_without_frozen_plan_fails_pre_dispatch(tmp_path: Path) -> None:
    authority, snapshot = _authority(tmp_path)
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    claim_key = work_actions._expected_claim_key(authority)
    steps = _base_steps(verify_result="passed", review_result="needs_human")
    run = _make_run(
        registry,
        authority=authority,
        claim_key=claim_key,
        current_phase="review",
        steps=steps,
        candidate_head=HEAD,
        verified_head=HEAD,
        facets=("needs_human",),
        planning_authority=(),  # 沒有冷凍 plan authority
    )
    with pytest.raises(RuntimeError, match="requires frozen plan authority"):
        work_actions.execute_work_action(
            args={
                "action": "retry-review",
                "repo": "acme/demo",
                "work_id": "demo",
                "issue": 12,
                "actor": "operator",
                "expected_candidate": HEAD,
            },
            requested_by="operator",
            snapshot_path=snapshot,
            state_path=tmp_path / "runs.json",
            workflow_registry=registry,
        )
    # pre-dispatch fail：完全沒有狀態變更
    unchanged = registry.get_workflow_run(run.run_id)
    assert unchanged.current_phase == "review"
    assert unchanged.facets == ("needs_human",)
    review_step = next(step for step in unchanged.steps if step.phase == "review")
    assert review_step.gate_result == "needs_human"


# ---------------------------------------------------------------------------
# AC4：source-owner／claim sequencing repair 不觸發 builder
# ---------------------------------------------------------------------------


def test_source_owner_conflict_blocks_before_any_builder_dispatch(tmp_path: Path) -> None:
    authority, snapshot = _authority(tmp_path)
    registry = JobRegistry(state_path=tmp_path / "jobs.json")

    calls: list[tuple[str, str, str | None]] = []

    def conflicting_starter(bound_authority, claim_key, reason):
        calls.append((bound_authority.work_id, claim_key, reason))
        raise RuntimeError(
            "source-owner transfer incomplete: source-owner-old still owns an overlapping issue"
        )

    result = work_actions.execute_work_action(
        args={
            "action": "start",
            "repo": "acme/demo",
            "work_id": "demo",
            "issue": 12,
            "actor": "operator",
        },
        requested_by="operator",
        snapshot_path=snapshot,
        state_path=tmp_path / "runs.json",
        workflow_registry=registry,
        workflow_starter=conflicting_starter,
        now=lambda: 200,
    )
    assert result["result"] == {
        "action": "blocked",
        "reason": "source-owner-repair-pending",
        "run": None,
        "retry_classification": "source_owner_repair",
    }
    # 從未成功建立任何 WorkflowRun（也就從未派過任何 builder job）。
    assert list(registry.list_workflow_runs()) == []
    assert len(calls) == 1


def test_unrelated_runtime_error_from_starter_still_propagates(tmp_path: Path) -> None:
    authority, snapshot = _authority(tmp_path)
    registry = JobRegistry(state_path=tmp_path / "jobs.json")

    def broken_starter(bound_authority, claim_key, reason):
        raise RuntimeError("unrelated infra failure")

    with pytest.raises(RuntimeError, match="unrelated infra failure"):
        work_actions.execute_work_action(
            args={
                "action": "start",
                "repo": "acme/demo",
                "work_id": "demo",
                "issue": 12,
                "actor": "operator",
            },
            requested_by="operator",
            snapshot_path=snapshot,
            state_path=tmp_path / "runs.json",
            workflow_registry=registry,
            workflow_starter=broken_starter,
            now=lambda: 200,
        )


# ---------------------------------------------------------------------------
# AC5：authority restart 只 invalidate 依賴已變更 authority hash 的 stage
# ---------------------------------------------------------------------------


def test_authority_restart_invalidates_only_verify_and_review_preserving_build(
    tmp_path: Path,
) -> None:
    old_authority, _ = _authority(tmp_path, source_revisions=["issue:12@open", "openspec:demo@1"])
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    claim_key = work_actions._expected_claim_key(old_authority)
    steps = _base_steps(verify_result="passed", review_result="passed")
    run = _make_run(
        registry,
        authority=old_authority,
        claim_key=claim_key,
        current_phase="review",
        steps=steps,
        candidate_head=HEAD,
        verified_head=HEAD,
        facets=(),
    )
    # WorkAuthority 宣告改變（issue 內容更新）——重新讀取新版 snapshot。
    new_snapshot = _snapshot(
        tmp_path / "snapshot.json",
        source_revisions=["issue:12@updated", "openspec:demo@1"],
    )
    new_authority = work_actions.load_work_authority(
        repo="acme/demo", work_id="demo", snapshot_path=new_snapshot
    )
    assert work_actions._expected_claim_key(new_authority) != claim_key

    result = work_actions.execute_work_action(
        args={"action": "resume", "repo": "acme/demo", "work_id": "demo", "issue": 12},
        requested_by="operator",
        snapshot_path=new_snapshot,
        state_path=tmp_path / "runs.json",
        workflow_registry=registry,
    )
    assert result["result"]["action"] == "resume"
    run_payload = result["result"]["run"]
    assert run_payload["current_phase"] == "verify"
    by_phase = {step["phase"]: step for step in run_payload["steps"]}
    assert by_phase["build"]["gate_result"] == "passed"  # candidate 保持不變
    assert by_phase["verify"]["gate_result"] == "pending"
    assert by_phase["review"]["gate_result"] == "pending"
    assert run_payload["candidate_head"] == HEAD  # candidate 沒被重建
    assert run_payload["verified_head"] is None
    assert run_payload["retry_classification"] == "authority_restart"
    assert run_payload["source_revision"] == work_actions.work_authority_digest(new_authority)


def test_authority_restart_does_not_invalidate_build_phase_run(tmp_path: Path) -> None:
    """build phase（candidate 尚未產出下游可評估內容）不套用 authority-restart
    精準 invalidation——沒有 verify/review 可 invalidate，維持原樣 resume。"""

    old_authority, _ = _authority(tmp_path, source_revisions=["issue:12@open", "openspec:demo@1"])
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    claim_key = work_actions._expected_claim_key(old_authority)
    steps = _base_steps(verify_result="pending", review_result="pending")
    _make_run(
        registry,
        authority=old_authority,
        claim_key=claim_key,
        current_phase="build",
        steps=steps,
        facets=(),
    )
    new_snapshot = _snapshot(
        tmp_path / "snapshot.json",
        source_revisions=["issue:12@updated", "openspec:demo@1"],
    )
    result = work_actions.execute_work_action(
        args={"action": "resume", "repo": "acme/demo", "work_id": "demo", "issue": 12},
        requested_by="operator",
        snapshot_path=new_snapshot,
        state_path=tmp_path / "runs.json",
        workflow_registry=registry,
    )
    run_payload = result["result"]["run"]
    assert run_payload["current_phase"] == "build"
    assert run_payload.get("retry_classification") is None


# ---------------------------------------------------------------------------
# 追加：retry_classification 在 WorkflowRun 上的 provenance 語意（供
# work_bridge._completion_draft 讀取寫入 CompletionRecord，maintainer 追加
# 派工 1）——一般 phase 推進（_manager_update_workflow_run）保持既有值不變，
# 直到下一次 retry 明確覆寫。
# ---------------------------------------------------------------------------


def test_retry_classification_persists_across_normal_workflow_updates(tmp_path: Path) -> None:
    authority, _ = _authority(tmp_path)
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    claim_key = work_actions._expected_claim_key(authority)
    steps = _base_steps(verify_result="needs_human", review_result="pending")
    run = _make_run(
        registry,
        authority=authority,
        claim_key=claim_key,
        current_phase="verify",
        steps=steps,
        candidate_head=HEAD,
        facets=("needs_human",),
    )
    reset = registry._manager_reset_workflow_for_retry_verify(
        run.run_id,
        expected_candidate=HEAD,
        retry_classification="model_repair",
    )
    assert reset.retry_classification == "model_repair"
    # 一般更新（例如 verify 通過推進到 review）不帶 retry_classification 參數時
    # 維持既有值——不會被悄悄清成 None。
    advanced = registry._manager_update_workflow_run(
        run.run_id,
        current_phase="review",
    )
    assert advanced.retry_classification == "model_repair"


# ---------------------------------------------------------------------------
# _classify_retry(trigger=...)：#216 補齊三類判準（直接指定，不靠狀態反推）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("trigger", "expected"),
    [
        ("authority-restart", work_actions.RetryClassification.AUTHORITY_RESTART),
        ("review-handoff-failure", work_actions.RetryClassification.REVIEW_HANDOFF_FAILURE),
        ("source-owner-repair", work_actions.RetryClassification.SOURCE_OWNER_REPAIR),
    ],
)
def test_classify_retry_trigger_returns_expected_classification(trigger, expected) -> None:
    assert work_actions._classify_retry(None, None, trigger=trigger) == expected


def test_classify_retry_rejects_unknown_trigger() -> None:
    with pytest.raises(ValueError, match="不支援的 trigger"):
        work_actions._classify_retry(None, None, trigger="not-a-real-trigger")
