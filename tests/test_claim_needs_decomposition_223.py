"""#223（design #208 H.3）：Red band 收斂到 needs_decomposition 的 claim 層行為。

``claim.decomposition_route()`` 是 Red band 路由的純函式核心（拆分深度上限
2 層，逾限轉 needs_human）；``_validate_candidate``／``_resume_decision`` 則
負責讓一個已被 manager 標成 ``needs_decomposition`` 的 run，在 claim/resume
掃描時原樣浮現，不被誤判成一般 ``ongoing`` run 而繼續重試。
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from paulsha_cortex.coordinator.claim import (
    ClaimCandidate,
    WorkAuthority,
    build_claim_key,
    decide_auto_claim,
    decide_manual_start,
    decomposition_route,
    load_work_authority,
    work_authority_digest,
)


def _authority(tmp_path: Path) -> WorkAuthority:
    payload = {
        "schema": "work-items-snapshot/v1",
        "providers": {
            "github": {
                "provider_id": "github",
                "revision": "github-rev-1",
                "last_success_epoch": 950,
                "degraded": False,
            }
        },
        "work_items": [
            {
                "repo": "acme/demo",
                "work_id": "lifecycle",
                "mapped_issues": [14],
                "mapped_prs": [],
                "mapped_openspec": ["lifecycle"],
                "mapped_todo_paths": ["docs/todo.md"],
                "confirmed_todo": True,
                "auto_label": True,
                "source_revisions": ["issue:14@open", "openspec:lifecycle@abc"],
            }
        ],
    }
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return load_work_authority(repo="acme/demo", work_id="lifecycle", snapshot_path=path)


def _candidate(authority: WorkAuthority) -> ClaimCandidate:
    return ClaimCandidate(
        authority=authority,
        repo="acme/demo",
        work_id="lifecycle",
        source_revisions=("issue:14@open", "openspec:lifecycle@abc"),
        confirmed_todo=True,
        confirmed_issue=14,
        auto_label=True,
        active_run_id=None,
        active_claim_key=None,
    )


def _active_candidate(tmp_path: Path, *, active_status: str) -> ClaimCandidate:
    authority = _authority(tmp_path)
    candidate = _candidate(authority)
    claim_key = build_claim_key(candidate)
    return replace(
        candidate,
        active_run_id="run-1",
        active_claim_key=claim_key,
        active_status=active_status,
        active_snapshot_hash=authority.snapshot_hash,
        active_source_revisions=authority.source_revisions,
        active_provider_revision=authority.github_provider_revision,
        active_authority_digest=work_authority_digest(authority),
    )


def test_decomposition_route_stays_below_depth_limit() -> None:
    assert decomposition_route(decomposition_depth=0) == "needs_decomposition"
    assert decomposition_route(decomposition_depth=1) == "needs_decomposition"


def test_decomposition_route_escalates_to_needs_human_at_depth_limit() -> None:
    assert decomposition_route(decomposition_depth=2) == "needs_human"
    assert decomposition_route(decomposition_depth=3) == "needs_human"


def test_decomposition_route_rejects_non_negative_int() -> None:
    with pytest.raises(ValueError, match="非負整數"):
        decomposition_route(decomposition_depth=-1)
    with pytest.raises(ValueError, match="非負整數"):
        decomposition_route(decomposition_depth=True)  # bool 是 int 子類，須排除
    with pytest.raises(ValueError, match="非負整數"):
        decomposition_route(decomposition_depth="2")  # type: ignore[arg-type]


def test_manual_start_surfaces_needs_decomposition_without_resuming(tmp_path: Path) -> None:
    active = _active_candidate(tmp_path, active_status="needs_decomposition")
    decision = decide_manual_start(active, now_epoch=1_000)
    assert decision.action == "needs_decomposition"
    assert decision.reason == "decomposition-required"
    assert decision.run_id == "run-1"
    assert decision.claim_key == active.active_claim_key


def test_auto_claim_surfaces_needs_decomposition_without_resuming(tmp_path: Path) -> None:
    active = _active_candidate(tmp_path, active_status="needs_decomposition")
    decision = decide_auto_claim(active, now_epoch=1_000)
    assert decision.action == "needs_decomposition"
    assert decision.reason == "decomposition-required"


def test_active_status_whitelist_rejects_unknown_values(tmp_path: Path) -> None:
    active = _active_candidate(tmp_path, active_status="mystery-status")
    with pytest.raises(ValueError, match="active workflow status invalid"):
        decide_manual_start(active, now_epoch=1_000)
