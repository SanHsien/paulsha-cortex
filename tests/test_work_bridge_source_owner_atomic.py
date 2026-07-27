"""Guards against the vN -> vN+1 source-owner transfer race (#217, design #208 D).

hippo #41 v3->v4: issue #41 moved from one work_id's authority to another's
while the old work_id's WorkflowRun was still "ongoing" -- the
missing_issue / human-intervention-required run this issue must stop
reproducing. hippo #41 v5: once the old owner is properly terminalized
(superseded), the new owner's claim must not get spuriously persisted-block
either -- ``start_canonical_workflow`` is the "新 run 才可 claim" mounting
point design #208 D's four-step order (terminalize/supersede -> unlink/link
-> snapshot confirm -> claim) needs.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from paulsha_cortex.coordinator import work_bridge
from paulsha_cortex.coordinator.claim import load_work_authority
from paulsha_cortex.coordinator.registry import JobRegistry


def _repo(root: Path) -> Path:
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True
    )
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", "git@github.com:acme/demo.git"],
        check=True,
    )
    (root / "README.md").write_text("demo\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    return root


def _snapshot(path: Path, *, work_id: str, issues: tuple[int, ...]) -> Path:
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
                        "work_id": work_id,
                        "mapped_issues": list(issues),
                        "mapped_prs": [],
                        "mapped_openspec": [work_id],
                        "mapped_todo_paths": ["docs/todo.md"],
                        "confirmed_todo": True,
                        "auto_label": False,
                        "source_revisions": ["source-rev-1"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _create_ongoing_run(registry: JobRegistry, *, authority, claim_key: str, issue: int) -> object:
    return registry._manager_create_workflow_run(
        work_id=authority.work_id,
        repo=authority.repo,
        claim_key=claim_key,
        source_revision="source-rev",
        workspace_root="/workspace",
        combo="feature-oneshot",
        current_phase="build",
        steps=(),
        issue_refs=(f"{authority.repo}#{issue}",),
        openspec_refs=(authority.work_id,),
    )


def test_new_owner_claim_is_refused_while_old_owner_run_still_ongoing(tmp_path: Path) -> None:
    """hippo #41 v3->v4: the old owner's ongoing run must block a new-owner claim."""

    workspace = _repo(tmp_path / "workspace")
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    old_authority = load_work_authority(
        repo="acme/demo",
        work_id="source-owner-old",
        snapshot_path=_snapshot(tmp_path / "old.json", work_id="source-owner-old", issues=(41,)),
    )
    _create_ongoing_run(registry, authority=old_authority, claim_key="claim:v1:" + "1" * 64, issue=41)

    new_authority = load_work_authority(
        repo="acme/demo",
        work_id="source-owner-new",
        snapshot_path=_snapshot(tmp_path / "new.json", work_id="source-owner-new", issues=(41,)),
    )

    with pytest.raises(RuntimeError, match="source-owner transfer incomplete"):
        work_bridge.start_canonical_workflow(
            registry=registry,
            authority=new_authority,
            claim_key="claim:v1:" + "2" * 64,
            coordinator_root=tmp_path / "coordinator",
            explicit_repo_root=workspace,
            needs_human_reason="missing-issue",
        )

    # The "舊 owner 仍在 snapshot 而新 run 已 start" intermediate state must
    # never materialize: no run for the new owner may exist yet.
    assert [run.work_id for run in registry.list_workflow_runs()] == ["source-owner-old"]


def test_new_owner_claim_succeeds_once_old_owner_run_is_terminal(tmp_path: Path) -> None:
    """hippo #41 v5: a properly-terminalized transfer must not persist-block the new owner."""

    workspace = _repo(tmp_path / "workspace")
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    old_authority = load_work_authority(
        repo="acme/demo",
        work_id="source-owner-old",
        snapshot_path=_snapshot(tmp_path / "old.json", work_id="source-owner-old", issues=(41,)),
    )
    old_run = _create_ongoing_run(
        registry, authority=old_authority, claim_key="claim:v1:" + "1" * 64, issue=41
    )
    # Step 1 of design #208 D: terminalize/supersede the old owner first.
    registry._manager_abandon_workflow_run(old_run.run_id, evidence_ref="evidence://old-abandon")

    new_authority = load_work_authority(
        repo="acme/demo",
        work_id="source-owner-new",
        snapshot_path=_snapshot(tmp_path / "new.json", work_id="source-owner-new", issues=(41,)),
    )

    new_run = work_bridge.start_canonical_workflow(
        registry=registry,
        authority=new_authority,
        claim_key="claim:v1:" + "2" * 64,
        coordinator_root=tmp_path / "coordinator",
        explicit_repo_root=workspace,
        needs_human_reason="missing-issue",
    )
    assert new_run.work_id == "source-owner-new"
    assert new_run.issue_refs == ("acme/demo#41",)


def test_disjoint_issue_ownership_does_not_block_new_claim(tmp_path: Path) -> None:
    """A different work_id's ongoing run on an unrelated issue must not block."""

    workspace = _repo(tmp_path / "workspace")
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    other_authority = load_work_authority(
        repo="acme/demo",
        work_id="unrelated",
        snapshot_path=_snapshot(tmp_path / "other.json", work_id="unrelated", issues=(99,)),
    )
    _create_ongoing_run(registry, authority=other_authority, claim_key="claim:v1:" + "3" * 64, issue=99)

    new_authority = load_work_authority(
        repo="acme/demo",
        work_id="source-owner-new",
        snapshot_path=_snapshot(tmp_path / "new.json", work_id="source-owner-new", issues=(41,)),
    )

    new_run = work_bridge.start_canonical_workflow(
        registry=registry,
        authority=new_authority,
        claim_key="claim:v1:" + "4" * 64,
        coordinator_root=tmp_path / "coordinator",
        explicit_repo_root=workspace,
        needs_human_reason="missing-issue",
    )
    assert new_run.work_id == "source-owner-new"
