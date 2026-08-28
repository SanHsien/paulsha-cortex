"""Focused tests for issue #206: per-row authority isolation + structured
diagnostics in ``claim.load_work_authorities``/``load_work_authority``.

Reproduces the durable "GitHub provider authority invalid" recurrence: one
repo's canonical GitHub provider entry is missing/invalid while an unrelated
repo in the same snapshot is healthy. Before this fix, a single bad row
aborted the *entire* ``load_work_authorities()`` load, so a target repo's
work-action was blocked by fleet noise from a repo it has nothing to do
with. The fix must keep fail-closed for the bad row's own work item while
no longer letting it blast-radius other repos.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paulsha_cortex.coordinator.claim import (
    AuthorityValidationError,
    load_work_authorities,
    load_work_authority,
)


def _canonical_row(
    *,
    repo: str,
    work_id: str,
    todo_ref: str = "docs/todo.md",
) -> dict:
    return {
        "repo": repo,
        "work_id": work_id,
        "sources": [
            {
                "confidence": "confirmed",
                "kind": "todo",
                "ref": todo_ref,
                "source_id": f"todo:{work_id}",
                "revision": "todo-rev-1",
            }
        ],
    }


def _healthy_provider(*, revision: str = "gh-rev-1", last_success_at: str = "2026-07-20T00:00:00Z") -> dict:
    return {"status": "ok", "revision": revision, "last_success_at": last_success_at}


def _write_snapshot(path: Path, *, providers: dict, work_items: list[dict]) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": "work-items-snapshot/v1",
                "providers": providers,
                "work_items": work_items,
            }
        ),
        encoding="utf-8",
    )
    return path


def _two_repo_snapshot(tmp_path: Path, *, broken_provider: dict | None) -> Path:
    """repo A (``acme/broken``) has an invalid/missing provider; repo B
    (``acme/healthy``) is fully healthy. ``broken_provider=None`` omits the
    provider entry entirely (missing); a dict with a bad ``status`` field
    exercises the invalid-but-present case.
    """

    providers = {"github:acme/healthy": _healthy_provider()}
    if broken_provider is not None:
        providers["github:acme/broken"] = broken_provider
    return _write_snapshot(
        tmp_path / "snapshot.json",
        providers=providers,
        work_items=[
            _canonical_row(repo="acme/broken", work_id="broken-work"),
            _canonical_row(repo="acme/healthy", work_id="healthy-work"),
        ],
    )


# --- AC4 / 測試要求 1：跨 repo 不誤阻斷 -------------------------------------


def test_unrelated_repo_bad_provider_does_not_block_healthy_repo(tmp_path: Path) -> None:
    snapshot = _two_repo_snapshot(tmp_path, broken_provider=None)

    healthy = load_work_authority(repo="acme/healthy", work_id="healthy-work", snapshot_path=snapshot)
    assert healthy.repo == "acme/healthy"
    assert healthy.work_id == "healthy-work"

    with pytest.raises(AuthorityValidationError) as excinfo:
        load_work_authority(repo="acme/broken", work_id="broken-work", snapshot_path=snapshot)
    assert excinfo.value.repo == "acme/broken"
    assert excinfo.value.reason_code.startswith("provider-authority-")


def test_invalid_but_present_provider_also_isolated_per_repo(tmp_path: Path) -> None:
    snapshot = _two_repo_snapshot(
        tmp_path,
        broken_provider={"status": "degraded", "revision": "gh-rev-x", "last_success_at": "2026-07-20T00:00:00Z"},
    )

    healthy = load_work_authority(repo="acme/healthy", work_id="healthy-work", snapshot_path=snapshot)
    assert healthy.work_id == "healthy-work"

    with pytest.raises(AuthorityValidationError) as excinfo:
        load_work_authority(repo="acme/broken", work_id="broken-work", snapshot_path=snapshot)
    assert excinfo.value.reason_code == "provider-authority-invalid-canonical"
    assert excinfo.value.field == "status"


# --- 測試要求 2：fail-closed 未鬆動 -----------------------------------------


def test_bad_row_work_item_absent_from_load_work_authorities(tmp_path: Path) -> None:
    snapshot = _two_repo_snapshot(tmp_path, broken_provider=None)
    authorities = load_work_authorities(snapshot_path=snapshot)
    identities = {(authority.repo, authority.work_id) for authority in authorities}
    assert identities == {("acme/healthy", "healthy-work")}
    assert ("acme/broken", "broken-work") not in identities


# --- 測試要求 3：canonical 與 legacy reason 分離 ----------------------------


def test_canonical_and_legacy_provider_failures_use_distinct_reason_codes(tmp_path: Path) -> None:
    canonical_snapshot = _two_repo_snapshot(tmp_path, broken_provider=None)
    with pytest.raises(AuthorityValidationError) as canonical_excinfo:
        load_work_authority(repo="acme/broken", work_id="broken-work", snapshot_path=canonical_snapshot)

    legacy_snapshot = _write_snapshot(
        tmp_path / "legacy-snapshot.json",
        providers={
            "github": {
                "provider_id": "github",
                "revision": "gh-1",
                "last_success_epoch": 100,
                "degraded": True,
            }
        },
        work_items=[
            {
                "repo": "acme/demo",
                "work_id": "legacy-work",
                "mapped_issues": [1],
                "mapped_prs": [],
                "mapped_openspec": [],
                "mapped_todo_paths": ["docs/todo.md"],
                "confirmed_todo": True,
                "auto_label": False,
                "source_revisions": ["source-rev-1"],
            }
        ],
    )
    with pytest.raises(AuthorityValidationError) as legacy_excinfo:
        load_work_authority(repo="acme/demo", work_id="legacy-work", snapshot_path=legacy_snapshot)

    assert canonical_excinfo.value.reason_code != legacy_excinfo.value.reason_code
    assert "canonical" in canonical_excinfo.value.reason_code
    assert "legacy" in legacy_excinfo.value.reason_code


def test_legacy_row_level_provider_missing_uses_legacy_reason_code(tmp_path: Path) -> None:
    # No "github" key at all in providers -> legacy row's own provider lookup
    # (not the snapshot-level degraded gate) is what fails.
    snapshot = _write_snapshot(
        tmp_path / "legacy-missing.json",
        providers={},
        work_items=[
            {
                "repo": "acme/demo",
                "work_id": "legacy-work",
                "mapped_issues": [1],
                "mapped_prs": [],
                "mapped_openspec": [],
                "mapped_todo_paths": ["docs/todo.md"],
                "confirmed_todo": True,
                "auto_label": False,
                "source_revisions": ["source-rev-1"],
            }
        ],
    )
    with pytest.raises(AuthorityValidationError) as excinfo:
        load_work_authority(repo="acme/demo", work_id="legacy-work", snapshot_path=snapshot)
    assert excinfo.value.reason_code == "provider-authority-missing-legacy"


# --- 測試要求 4：診斷內容含必要欄位、不含機密 -------------------------------


def test_diagnostics_contain_repo_provider_field_and_no_secrets(tmp_path: Path) -> None:
    snapshot = _two_repo_snapshot(tmp_path, broken_provider=None)
    with pytest.raises(AuthorityValidationError) as excinfo:
        load_work_authority(repo="acme/broken", work_id="broken-work", snapshot_path=snapshot)
    exc = excinfo.value
    assert exc.repo == "acme/broken"
    assert exc.provider_id == "github:acme/broken"
    assert exc.field is not None
    assert exc.reason_code

    rendered = str(exc)
    assert "acme/broken" in rendered
    assert str(tmp_path) not in rendered
    assert "/home/" not in rendered
    assert not rendered.startswith("/")


# --- 測試要求 5：既有 regression（#217 雙 owner／identity 重複）維持 raise -----


def test_duplicate_identity_rows_still_raise(tmp_path: Path) -> None:
    snapshot = _write_snapshot(
        tmp_path / "dup-identity.json",
        providers={"github:acme/demo": _healthy_provider()},
        work_items=[
            _canonical_row(repo="acme/demo", work_id="dup-work"),
            _canonical_row(repo="acme/demo", work_id="dup-work"),
        ],
    )
    with pytest.raises(ValueError, match="missing or ambiguous"):
        load_work_authorities(snapshot_path=snapshot)


def test_dual_owner_same_issue_still_raises_217_regression(tmp_path: Path) -> None:
    providers = {"github:acme/demo": _healthy_provider()}
    row_old = _canonical_row(repo="acme/demo", work_id="owner-old")
    row_old["sources"].append(
        {
            "confidence": "confirmed",
            "kind": "github_issue",
            "ref": "acme/demo#41",
            "source_id": "issue:41",
            "revision": "issue-rev-1",
            "status": "open",
        }
    )
    row_new = _canonical_row(repo="acme/demo", work_id="owner-new")
    row_new["sources"].append(
        {
            "confidence": "confirmed",
            "kind": "github_issue",
            "ref": "acme/demo#41",
            "source_id": "issue:41",
            "revision": "issue-rev-1",
            "status": "open",
        }
    )
    snapshot = _write_snapshot(
        tmp_path / "dual-owner.json",
        providers=providers,
        work_items=[row_old, row_new],
    )
    with pytest.raises(ValueError, match="missing or ambiguous"):
        load_work_authorities(snapshot_path=snapshot)
