"""#370: a canonical GitHub provider row degraded by a *rate limit* must get
a distinct, recognizable reason code from a genuinely invalid/malformed
provider row -- upstream (durable done records, Manager logs, resume/backoff
handling) needs to tell "temporarily rate limited, will resolve itself" apart
from "authority is actually broken" without re-parsing message text.

Complements ``tests/test_claim_authority_isolation_206.py`` (which already
locks down the canonical/legacy reason-code split); this file is scoped to
the rate-limit-specific split *within* the canonical reason space.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paulsha_cortex.coordinator.claim import (
    REASON_PROVIDER_INVALID_CANONICAL,
    AuthorityValidationError,
    load_work_authority,
)


def _canonical_row(*, repo: str, work_id: str) -> dict:
    return {
        "repo": repo,
        "work_id": work_id,
        "sources": [
            {
                "confidence": "confirmed",
                "kind": "todo",
                "ref": "docs/todo.md",
                "source_id": f"todo:{work_id}",
                "revision": "todo-rev-1",
            }
        ],
    }


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


def test_rate_limit_degraded_provider_gets_dedicated_reason_code(tmp_path: Path) -> None:
    snapshot = _write_snapshot(
        tmp_path / "snapshot.json",
        providers={
            "github:acme/demo": {
                "status": "degraded",
                "revision": "gh-rev-1",
                "last_success_at": "2026-08-07T11:19:26Z",
                "diagnostics": [
                    "github rate limit exceeded",
                    "github:acme/demo stale",
                ],
            }
        },
        work_items=[_canonical_row(repo="acme/demo", work_id="rate-limited-work")],
    )

    with pytest.raises(AuthorityValidationError) as excinfo:
        load_work_authority(repo="acme/demo", work_id="rate-limited-work", snapshot_path=snapshot)

    exc = excinfo.value
    # Distinct from the generic invalid-provider reason -- and NOT that one.
    assert exc.reason_code != REASON_PROVIDER_INVALID_CANONICAL
    assert "rate-limit" in exc.reason_code
    assert "canonical" in exc.reason_code
    assert exc.field == "status"
    assert exc.repo == "acme/demo"
    assert exc.provider_id == "github:acme/demo"


def test_non_rate_limit_degraded_provider_still_uses_generic_invalid_reason(tmp_path: Path) -> None:
    """A provider that's merely stale/degraded for an unrelated reason (no
    rate-limit wording in diagnostics) must NOT be misclassified as
    rate-limited -- it keeps the existing generic reason code."""
    snapshot = _write_snapshot(
        tmp_path / "snapshot.json",
        providers={
            "github:acme/demo": {
                "status": "degraded",
                "revision": "gh-rev-1",
                "last_success_at": "2026-08-07T11:19:26Z",
                "diagnostics": ["github API returned malformed JSON"],
            }
        },
        work_items=[_canonical_row(repo="acme/demo", work_id="broken-work")],
    )

    with pytest.raises(AuthorityValidationError) as excinfo:
        load_work_authority(repo="acme/demo", work_id="broken-work", snapshot_path=snapshot)

    assert excinfo.value.reason_code == REASON_PROVIDER_INVALID_CANONICAL


def test_authority_validation_error_remains_a_value_error_for_rate_limit_reason(tmp_path: Path) -> None:
    """Existing broad ``except ValueError`` call sites (e.g.
    ``mapped_issue_titles``) must keep working unchanged for the new reason
    code -- it's still a fail-closed "authority unavailable" outcome for
    them, just distinguishable for callers that care (resume/backoff)."""
    snapshot = _write_snapshot(
        tmp_path / "snapshot.json",
        providers={
            "github:acme/demo": {
                "status": "degraded",
                "revision": "gh-rev-1",
                "last_success_at": "2026-08-07T11:19:26Z",
                "diagnostics": ["github rate limit exceeded"],
            }
        },
        work_items=[_canonical_row(repo="acme/demo", work_id="rate-limited-work")],
    )

    with pytest.raises(ValueError):
        load_work_authority(repo="acme/demo", work_id="rate-limited-work", snapshot_path=snapshot)
