from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from paulsha_cortex.coordinator import work_actions
from paulsha_cortex.coordinator.claim import (
    ClaimCandidate,
    WorkAuthority,
    _resume_decision,
    build_claim_key,
    load_work_authority,
    work_authority_digest,
)
from paulsha_cortex.coordinator.registry import JobRegistry

RECOVERY_ACTION = "recover-planning"


def _snapshot(
    path: Path,
    *,
    issues=(12,),
    source_revisions=("issue:12@open", "openspec:demo@1"),
    provider_revision="gh-1",
    auto_label=True,
    prs=(8,),
    changes=("demo",),
    todo_paths=("docs/todo.md",),
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "work-items-snapshot/v1",
                "providers": {
                    "github": {
                        "provider_id": "github",
                        "revision": provider_revision,
                        "last_success_epoch": 100,
                        "degraded": False,
                    }
                },
                "work_items": [
                    {
                        "repo": "acme/demo",
                        "work_id": "demo",
                        "mapped_issues": list(issues),
                        "mapped_prs": list(prs),
                        "mapped_openspec": list(changes),
                        "mapped_todo_paths": list(todo_paths),
                        "confirmed_todo": True,
                        "auto_label": auto_label,
                        "source_revisions": list(source_revisions),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _authority(tmp_path: Path) -> WorkAuthority:
    return load_work_authority(
        repo="acme/demo",
        work_id="demo",
        snapshot_path=_snapshot(tmp_path / "snapshot.json"),
    )


def _candidate(authority: WorkAuthority) -> ClaimCandidate:
    return ClaimCandidate(
        authority=authority,
        repo="acme/demo",
        work_id="demo",
        source_revisions=authority.source_revisions,
        confirmed_todo=authority.confirmed_todo,
        confirmed_issue=12,
        auto_label=False,
        active_run_id=None,
        active_claim_key=None,
    )


def _needs_human_candidate(tmp_path: Path) -> ClaimCandidate:
    authority = _authority(tmp_path)
    base = _candidate(authority)
    return replace(
        base,
        active_run_id="workflow-" + "a" * 20,
        active_claim_key=build_claim_key(base),
        active_status="needs_human",
        active_snapshot_hash=authority.snapshot_hash,
        active_source_revisions=authority.source_revisions,
        active_provider_revision=authority.github_provider_revision,
        active_authority_digest=work_authority_digest(authority),
    )


def _evidence_record(root: Path, *, run_id: str, classification: str, reason: str) -> str:
    evidence = root / "evidence" / "planning-recovery"
    evidence.mkdir(parents=True, exist_ok=True)
    target = evidence / f"{run_id}-{classification}.json"
    target.write_text(
        json.dumps(
            {
                "schema": "cortex-planning-failure/v1",
                "run_id": run_id,
                "classification": classification,
                "reason": reason,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return str(target)


def _start_define_run(*, snapshot: Path, state: Path, registry: JobRegistry) -> str:
    started = work_actions.execute_work_action(
        args={"action": "start", "repo": "acme/demo", "work_id": "demo"},
        requested_by="operator",
        snapshot_path=snapshot,
        state_path=state,
        now=lambda: 200,
        workflow_registry=registry,
    )
    return started["result"]["run"]["run_id"]


def _seed_planning_failure_run(
    tmp_path: Path, *,
    classification: str,
    reason: str,
) -> tuple[str, JobRegistry, Path, Path]:
    snapshot = _snapshot(tmp_path / "snapshot.json")
    state = tmp_path / "runs.json"
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    run_id = _start_define_run(
        snapshot=snapshot,
        state=state,
        registry=registry,
    )
    failure_record = _evidence_record(
        tmp_path,
        run_id=run_id,
        classification=classification,
        reason=reason,
    )
    registry._manager_update_workflow_run(
        run_id,
        current_phase="define",
        facets=("needs_human",),
        attempts={"claim": 1, "define": 1},
        evidence_refs=(failure_record,),
    )
    return run_id, registry, state, snapshot


def _run_recovery_action(
    *,
    run_id: str,
    snapshot: Path,
    state: Path,
    registry: JobRegistry,
    expected_run_id: str | None = None,
    classification: str,
    reason: str,
) -> dict:
    args: dict[str, object] = {
        "action": RECOVERY_ACTION,
        "repo": "acme/demo",
        "work_id": "demo",
        "failure_classification": classification,
        "failure_reason": reason,
    }
    if expected_run_id is not None:
        args["expected_run_id"] = expected_run_id
    return work_actions.execute_work_action(
        args=args,
        requested_by="operator",
        snapshot_path=snapshot,
        state_path=state,
        now=lambda: 200,
        workflow_registry=registry,
    )


def test_environment_failure_is_recoverable(tmp_path: Path) -> None:
    run_id, registry, state, snapshot = _seed_planning_failure_run(
        tmp_path,
        classification="environment",
        reason="planning identity probe unavailable",
    )
    before = registry.get_workflow_run(run_id)

    recovered = _run_recovery_action(
        run_id=run_id,
        snapshot=snapshot,
        state=state,
        registry=registry,
        expected_run_id=run_id,
        classification="environment",
        reason="planning identity probe unavailable",
    )
    result_run = recovered["result"]["run"]

    assert recovered["result"]["action"] == "recovered"
    assert result_run["run_id"] == run_id
    assert result_run["current_phase"] in {"plan", "build", "verify", "review", "ship"}
    assert result_run["source_revision"] == before.source_revision


def test_content_failure_is_not_recoverable(tmp_path: Path) -> None:
    run_id, registry, state, snapshot = _seed_planning_failure_run(
        tmp_path,
        classification="content",
        reason="blocking marker missing",
    )
    with pytest.raises(Exception, match="content"):
        _run_recovery_action(
            run_id=run_id,
            snapshot=snapshot,
            state=state,
            registry=registry,
            expected_run_id=run_id,
            classification="content",
            reason="blocking marker missing",
        )


def test_resume_returns_reason_and_next_actions(tmp_path: Path) -> None:
    decision = _resume_decision(_needs_human_candidate(tmp_path))

    assert decision.action == "needs_human"
    assert decision.reason == "human-intervention-required"
    assert hasattr(decision, "next_actions"), "needs_human resume decision must expose next_actions"
    next_actions = decision.next_actions
    assert isinstance(next_actions, (list, tuple))
    assert next_actions
    assert "abandon" in next_actions


def test_abandon_allows_reclaim(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path / "snapshot.json", prs=())
    state = tmp_path / "runs.json"
    registry = JobRegistry(state_path=tmp_path / "jobs.json")

    started = work_actions.execute_work_action(
        args={"action": "start", "repo": "acme/demo", "work_id": "demo"},
        requested_by="operator",
        snapshot_path=snapshot,
        state_path=state,
        now=lambda: 200,
        workflow_registry=registry,
    )
    run_id = started["result"]["run"]["run_id"]

    work_actions.execute_work_action(
        args={
            "action": "abandon",
            "repo": "acme/demo",
            "work_id": "demo",
            "issue": 12,
            "actor": "operator",
            "expected_run_id": run_id,
            "reason": "temp planning recover test",
        },
        requested_by="operator",
        snapshot_path=snapshot,
        state_path=state,
        now=lambda: 201,
        workflow_registry=registry,
    )

    reclaimed = work_actions.execute_work_action(
        args={"action": "start", "repo": "acme/demo", "work_id": "demo"},
        requested_by="operator",
        snapshot_path=snapshot,
        state_path=state,
        now=lambda: 202,
        workflow_registry=registry,
    )

    assert reclaimed["result"]["action"] == "claim"
    assert reclaimed["result"]["run"]["run_id"] != run_id


def test_existing_blocked_runs_unaffected(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path / "snapshot.json")
    state = tmp_path / "runs.json"
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    started = work_actions.execute_work_action(
        args={"action": "start", "repo": "acme/demo", "work_id": "demo"},
        requested_by="operator",
        snapshot_path=snapshot,
        state_path=state,
        now=lambda: 200,
        workflow_registry=registry,
    )
    run_id = started["result"]["run"]["run_id"]
    registry._manager_update_workflow_run(
        run_id,
        status="superseded",
        facets=("blocked",),
        evidence_refs=(),
    )

    with pytest.raises(Exception, match="blocked|persisted-block"):
        _run_recovery_action(
            run_id=run_id,
            snapshot=snapshot,
            state=state,
            registry=registry,
            expected_run_id=run_id,
            classification="environment",
            reason="legacy blocked run should stay blocked",
        )


def test_recovery_requires_expected_run_id(tmp_path: Path) -> None:
    run_id, registry, state, snapshot = _seed_planning_failure_run(
        tmp_path,
        classification="environment",
        reason="identity unavailable",
    )
    with pytest.raises(Exception, match="expected_run_id"):
        _run_recovery_action(
            run_id=run_id,
            snapshot=snapshot,
            state=state,
            registry=registry,
            classification="environment",
            reason="identity unavailable",
        )


def test_recovery_is_idempotent(tmp_path: Path) -> None:
    run_id, registry, state, snapshot = _seed_planning_failure_run(
        tmp_path,
        classification="environment",
        reason="identity recovered after runtime restart",
    )
    first = _run_recovery_action(
        run_id=run_id,
        snapshot=snapshot,
        state=state,
        registry=registry,
        expected_run_id=run_id,
        classification="environment",
        reason="identity recovered after runtime restart",
    )
    runs_after_first = len(registry.list_workflow_runs())

    second = _run_recovery_action(
        run_id=run_id,
        snapshot=snapshot,
        state=state,
        registry=registry,
        expected_run_id=run_id,
        classification="environment",
        reason="identity recovered after runtime restart",
    )
    runs_after_second = len(registry.list_workflow_runs())

    assert first["result"]["run"]["run_id"] == second["result"]["run"]["run_id"]
    assert runs_after_second == runs_after_first
