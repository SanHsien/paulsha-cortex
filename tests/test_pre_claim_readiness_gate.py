"""Focused tests for the #211 readiness gate mounted on work_actions._claim_action.

AC5 (issue #211): any pre-claim readiness check failure must not create a
workflow job, worktree, or model session. These tests assert the gate blocks
*before* ``workflow_starter`` is ever invoked, for both the manual claim path
(``_claim_action`` / ``execute_work_action``) and the automatic scan path
(``run_auto_claim_scan``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paulsha_cortex.coordinator import claim_readiness as cr
from paulsha_cortex.coordinator import work_actions
from paulsha_cortex.coordinator.claim import WorkAuthority


def _never_start(*_args, **_kwargs):
    raise AssertionError("readiness failure must not create a workflow job/worktree/model session")


def _snapshot(path: Path, *, issues=(211,), auto_label: bool = True) -> Path:
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
                        "mapped_issues": list(issues),
                        "mapped_prs": [],
                        "mapped_openspec": ["demo"],
                        "mapped_todo_paths": ["docs/todo.md"],
                        "confirmed_todo": True,
                        "auto_label": auto_label,
                        "source_revisions": ["issue:211@open", "openspec:demo@1"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _authority(tmp_path: Path) -> WorkAuthority:
    snapshot = _snapshot(tmp_path / "snapshot.json")
    return work_actions.load_work_authority(repo="acme/demo", work_id="demo", snapshot_path=snapshot)


def _retryable_outcome(reason: str = "stale-base", failed_check: str = "base_sha") -> cr.ReadinessOutcome:
    return cr.ReadinessOutcome(
        ready=False,
        frozen=None,
        failed_check=failed_check,
        reason=reason,
        terminal=False,
        checks_run=("local_scope", failed_check),
    )


def _terminal_outcome() -> cr.ReadinessOutcome:
    return cr.ReadinessOutcome(
        ready=False,
        frozen=None,
        failed_check="local_scope",
        reason="policy-scope-conflict",
        terminal=True,
        checks_run=("local_scope",),
    )


def _passing_outcome(authority: WorkAuthority) -> cr.ReadinessOutcome:
    from paulsha_cortex.coordinator.claim import work_authority_digest

    frozen = cr.FrozenReadinessSet(
        schema=cr.FROZEN_READINESS_SET_SCHEMA,
        repo=authority.repo,
        work_id=authority.work_id,
        base_sha="a" * 40,
        planning_authority_hashes=(work_authority_digest(authority),),
        monitor_snapshot_revision=authority.snapshot_hash,
        issue_ref="acme/demo#211",
        executor_identity="agy:gemini",
        frozen_at_epoch=1000.0,
        live_probe_ttl_cached=False,
    )
    return cr.ReadinessOutcome(
        ready=True,
        frozen=frozen,
        failed_check=None,
        reason=None,
        terminal=False,
        checks_run=cr.CHECK_ORDER,
    )


# ---------------------------------------------------------------------------
# Backward compatibility: no readiness_checker supplied changes nothing.
# ---------------------------------------------------------------------------


def test_claim_action_without_readiness_checker_behaves_as_before(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    started = []

    def starter(authority_arg, claim_key, reason):
        started.append((authority_arg.work_id, claim_key, reason))
        return _FakeRun(claim_key)

    result = work_actions._claim_action(
        args={"action": "start", "issue": 211},
        authority=authority,
        now_epoch=200,
        state_path=tmp_path / "runs.json",
        workflow_starter=starter,
    )
    assert result["action"] == "claim"
    assert len(started) == 1


class _FakeRun:
    def __init__(self, claim_key: str) -> None:
        self.claim_key = claim_key
        self.run_id = "workflow-" + "a" * 20
        self.repo = "acme/demo"
        self.work_id = "demo"
        self.status = "ongoing"
        self.current_phase = "define"
        self.facets = ()
        self.issue_refs = ("acme/demo#211",)
        self.openspec_refs = ("demo",)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "repo": self.repo,
            "work_id": self.work_id,
            "claim_key": self.claim_key,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# AC5: any readiness failure blocks before workflow_starter is ever called.
# ---------------------------------------------------------------------------


def test_retryable_readiness_failure_blocks_without_creating_a_run(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    result = work_actions._claim_action(
        args={"action": "start", "issue": 211},
        authority=authority,
        now_epoch=200,
        state_path=tmp_path / "runs.json",
        workflow_starter=_never_start,
        readiness_checker=lambda _authority, _issue_ref: _retryable_outcome(),
    )
    assert result == {
        "action": "blocked",
        "reason": "stale-base",
        "run": None,
        "readiness_failed_check": "base_sha",
    }


def test_terminal_readiness_failure_routes_to_needs_human_without_a_run(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    result = work_actions._claim_action(
        args={"action": "start", "issue": 211},
        authority=authority,
        now_epoch=200,
        state_path=tmp_path / "runs.json",
        workflow_starter=_never_start,
        readiness_checker=lambda _authority, _issue_ref: _terminal_outcome(),
    )
    assert result["action"] == "needs_human"
    assert result["reason"] == "policy-scope-conflict"
    assert result["run"] is None
    # Not routed through the normal needs_human tracking run: no run_id at
    # all means there is nothing to feed back into a retry loop.
    assert "run_id" not in result


def test_readiness_checker_receives_confirmed_issue_ref(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    seen = []

    def checker(_authority, issue_ref):
        seen.append(issue_ref)
        return _retryable_outcome()

    work_actions._claim_action(
        args={"action": "start", "issue": 211},
        authority=authority,
        now_epoch=200,
        state_path=tmp_path / "runs.json",
        workflow_starter=_never_start,
        readiness_checker=checker,
    )
    assert seen == ["acme/demo#211"]


def test_automatic_scan_readiness_failure_never_reads_workflow_starter(tmp_path: Path) -> None:
    """The automatic (cron) claim path must honour the same gate."""

    snapshot = _snapshot(tmp_path / "snapshot.json")
    state = tmp_path / "runs.json"

    def runner(argv, **kwargs):
        from types import SimpleNamespace

        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"labels": [{"name": "cortex:auto-on-going"}]}),
            stderr="",
        )

    from paulsha_cortex.coordinator.registry import JobRegistry

    registry = JobRegistry(state_path=state.parent / "jobs.json")
    results = work_actions.run_auto_claim_scan(
        snapshot_path=snapshot,
        state_path=state,
        now=lambda: 200,
        runner=runner,
        workflow_registry=registry,
        workflow_starter=_never_start,
        readiness_checker=lambda _authority, _issue_ref: _terminal_outcome(),
    )
    assert len(results) == 1
    assert results[0]["action"] == "needs_human"
    assert results[0]["reason"] == "policy-scope-conflict"


# ---------------------------------------------------------------------------
# AC2 (frozen set, not a boolean) round-trips through the claim result.
# ---------------------------------------------------------------------------


def test_passing_readiness_attaches_frozen_set_to_the_claimed_run(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    outcome = _passing_outcome(authority)
    started = []

    def starter(authority_arg, claim_key, reason):
        started.append(claim_key)
        return _FakeRun(claim_key)

    result = work_actions._claim_action(
        args={"action": "start", "issue": 211},
        authority=authority,
        now_epoch=200,
        state_path=tmp_path / "runs.json",
        workflow_starter=starter,
        readiness_checker=lambda _authority, _issue_ref: outcome,
    )
    assert result["action"] == "claim"
    assert len(started) == 1
    assert result["run"]["frozen_readiness"] == outcome.frozen.to_dict()
    assert result["run"]["frozen_readiness"]["base_sha"] == "a" * 40


def test_passing_readiness_persists_frozen_set_into_workflow_registry(tmp_path: Path) -> None:
    """#211 閉環另一半（verifier finding 2）：readiness 通過且給了真實
    workflow_registry 時，凍結集必須實際寫回 registry 的 WorkflowRun
    （dispatch 建 worktree 讀的是 registry，不是 API 回應 dict）。"""
    from paulsha_cortex.coordinator.registry import JobRegistry
    from paulsha_cortex.coordinator.workflow import WorkflowStep

    authority = _authority(tmp_path)
    outcome = _passing_outcome(authority)
    registry = JobRegistry(state_path=tmp_path / "jobs.json")

    def starter(authority_arg, claim_key, reason):
        return registry._manager_create_workflow_run(
            repo=authority_arg.repo,
            work_id=authority_arg.work_id,
            claim_key=claim_key,
            source_revision="rev-frozen",
            workspace_root=str(tmp_path),
            combo="feature-oneshot",
            current_phase="claim",
            steps=(
                WorkflowStep(
                    phase="claim", persona="manager", card="workflow-claim",
                    executor=None, model=None, domain=None, inputs=(), outputs=(),
                    gate_result="pending",
                ),
            ),
            issue_refs=tuple(
                f"{authority_arg.repo}#{n}" for n in authority_arg.mapped_issues
            ),
        )

    result = work_actions._claim_action(
        args={"action": "start", "issue": 211},
        authority=authority,
        now_epoch=200,
        state_path=tmp_path / "runs.json",
        workflow_registry=registry,
        workflow_starter=starter,
        readiness_checker=lambda _authority, _issue_ref: outcome,
    )
    assert result["action"] == "claim"
    persisted = registry.list_workflow_runs()[0]
    assert persisted.frozen_readiness == outcome.frozen.to_dict()
    assert persisted.frozen_readiness["base_sha"] == "a" * 40
