"""Focused tests for claim.py's snapshot-level unique-owner invariant (#217).

Design #208 D's source-owner transfer walks vN -> vN+1 through an
unlink/link window in ``.cortex/work-items.yaml``. If the durable monitor
snapshot is ever read back while two different work_ids both claim the same
GitHub issue as a confirmed source -- the literal "舊 owner 仍在 snapshot 而
新 run 已 start" intermediate state this issue must never let a claim
observe -- every ``load_work_authorities``/``load_work_authority`` call must
refuse rather than silently returning one arbitrary "winner".
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paulsha_cortex.coordinator.claim import (
    load_work_authorities,
    load_work_authority,
)


def _row(work_id: str, *, issues: list[int]) -> dict:
    return {
        "repo": "acme/demo",
        "work_id": work_id,
        "mapped_issues": issues,
        "mapped_prs": [],
        "mapped_openspec": [],
        "mapped_todo_paths": ["docs/todo.md"],
        "confirmed_todo": True,
        "auto_label": False,
        "source_revisions": ["source-rev-1"],
    }


def _snapshot(path: Path, *, work_items: list[dict]) -> Path:
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
                "work_items": work_items,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_snapshot_with_two_owners_for_same_issue_is_rejected(tmp_path: Path) -> None:
    """hippo #41 v3->v4: a mid-transfer snapshot must never yield two owners."""

    snapshot = _snapshot(
        tmp_path / "snapshot.json",
        work_items=[
            _row("source-owner-old", issues=[41]),
            _row("source-owner-new", issues=[41]),
        ],
    )
    with pytest.raises(ValueError, match="missing or ambiguous"):
        load_work_authorities(snapshot_path=snapshot)
    with pytest.raises(ValueError, match="missing or ambiguous"):
        load_work_authority(
            repo="acme/demo", work_id="source-owner-new", snapshot_path=snapshot
        )


def test_snapshot_after_transfer_completes_has_single_owner(tmp_path: Path) -> None:
    """Once unlink/link converge, only the new work_id maps the issue."""

    snapshot = _snapshot(
        tmp_path / "snapshot.json",
        work_items=[
            _row("source-owner-old", issues=[]),
            _row("source-owner-new", issues=[41]),
        ],
    )
    authorities = load_work_authorities(snapshot_path=snapshot)
    assert {
        authority.work_id: authority.mapped_issues for authority in authorities
    } == {
        "source-owner-old": (),
        "source-owner-new": (41,),
    }


def test_disjoint_issues_across_work_ids_are_unaffected(tmp_path: Path) -> None:
    """Two work_ids owning unrelated issues must not trip the guard."""

    snapshot = _snapshot(
        tmp_path / "snapshot.json",
        work_items=[
            _row("alpha", issues=[10]),
            _row("beta", issues=[11]),
        ],
    )
    authorities = load_work_authorities(snapshot_path=snapshot)
    assert len(authorities) == 2
