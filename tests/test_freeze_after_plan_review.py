"""#213（design #208 A.1）：freeze point 移至 plan review 通過之後。

lifecycle 改為 plan -> plan review -> 修訂 -> freeze -> build：在 planning.plan_review_gate()
（#212）尚未回傳 ready=True 之前，plan 修訂造成的 mapped_openspec/mapped_todo_paths/
source_revisions 飄移，不得被 claim.py 當成 authority 變更（觸發 supersede、生出新世代）。

驗收條件對應：
1. freeze point 位於 plan review 通過之後 —— planning.plan_review_freezes_authority()
   把 plan_review_gate() 的 outcome 對應到「是否可以 freeze」。
2. plan review 前的 plan 修訂不產生 supersede、不變更 authority hash —— claim.py
   _existing() 在 active_plan_review_passed=False 時改用 claim_identity_digest()
   （不含 mapped_openspec/mapped_todo_paths/source_revisions）判斷是否比對得上。
3. regression：plan 修訂不再導致 v3->v4 的 authority 世代增長（hippo #18 第 3、7 條）。
4. 既有合法 plan（plan review 已通過）仍可通過新順序（沿用完整 digest 比對，行為不變）。
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
    claim_identity_digest,
    decide_auto_claim,
    decide_manual_start,
    load_work_authority,
    work_authority_digest,
)
from paulsha_cortex.coordinator.planning import (
    PlanningArtifact,
    PlanReviewOutcome,
    plan_review_freezes_authority,
    plan_review_gate,
)


# --- fixtures --------------------------------------------------------------


def _authority(
    tmp_path: Path,
    *,
    label: str,
    mapped_openspec: tuple[str, ...] = ("lifecycle",),
    mapped_todo_paths: tuple[str, ...] = ("docs/todo.md",),
    source_revisions: tuple[str, ...] = ("issue:14@open", "openspec:lifecycle@abc"),
    issues: tuple[int, ...] = (14,),
) -> WorkAuthority:
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
                "mapped_issues": list(issues),
                "mapped_prs": [8],
                "mapped_openspec": list(mapped_openspec),
                "mapped_todo_paths": list(mapped_todo_paths),
                "confirmed_todo": True,
                "auto_label": True,
                "source_revisions": list(source_revisions),
            }
        ],
    }
    path = tmp_path / f"snapshot-{label}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return load_work_authority(repo="acme/demo", work_id="lifecycle", snapshot_path=path)


def _fresh_candidate(authority: WorkAuthority) -> ClaimCandidate:
    return ClaimCandidate(
        authority=authority,
        repo="acme/demo",
        work_id="lifecycle",
        source_revisions=authority.source_revisions,
        confirmed_todo=True,
        confirmed_issue=14,
        auto_label=True,
        active_run_id=None,
        active_claim_key=None,
    )


def _active_candidate(
    *,
    original: WorkAuthority,
    current: WorkAuthority,
    active_plan_review_passed: bool,
) -> ClaimCandidate:
    original_claim_key = build_claim_key(_fresh_candidate(original))
    return replace(
        _fresh_candidate(current),
        active_run_id="run-1",
        active_claim_key=original_claim_key,
        active_status="ongoing",
        active_snapshot_hash=original.snapshot_hash,
        active_source_revisions=original.source_revisions,
        active_provider_revision=original.github_provider_revision,
        active_authority_digest=work_authority_digest(original),
        active_plan_review_passed=active_plan_review_passed,
        active_claim_identity_digest=claim_identity_digest(original),
    )


# --- AC1: freeze point 位於 plan review 通過之後 ----------------------------


def _plan_text(*, tasks_body: str) -> str:
    return (
        "---\n"
        "invariant_count: 1\n"
        "artifact_classes: [code]\n"
        "status: accepted\n"
        "---\n"
        "## Tasks\n"
        f"{tasks_body}"
    )


def test_plan_review_freezes_authority_only_when_gate_ready() -> None:
    ready_plan = PlanningArtifact(
        kind="plan",
        ref="docs/superpowers/plans/demo.md",
        text=_plan_text(tasks_body="- 實作 code 變動\n"),
    )
    ready_outcome = plan_review_gate(
        plan_artifact=ready_plan,
        acceptance_surfaces=frozenset({"code"}),
        applicable_contract_rules=frozenset(),
    )
    assert isinstance(ready_outcome, PlanReviewOutcome)
    assert ready_outcome.ready is True
    assert plan_review_freezes_authority(ready_outcome) is True

    unready_plan = PlanningArtifact(
        kind="plan",
        ref="docs/superpowers/plans/demo.md",
        text=_plan_text(tasks_body="- 其他工作\n"),
    )
    unready_outcome = plan_review_gate(
        plan_artifact=unready_plan,
        acceptance_surfaces=frozenset({"code"}),
        applicable_contract_rules=frozenset(),
    )
    assert unready_outcome.ready is False
    assert plan_review_freezes_authority(unready_outcome) is False


def test_plan_review_freezes_authority_rejects_terminal_outcome_too() -> None:
    terminal_outcome = PlanReviewOutcome(
        ready=False,
        failed_check="contract_compatibility",
        reason="policy-scope-conflict: R-09",
        terminal=True,
        checks_run=("completeness", "contract_compatibility"),
        observations={},
    )
    assert plan_review_freezes_authority(terminal_outcome) is False


# --- claim_identity_digest：穩定 identity（不含 plan 產物欄位）-------------


def test_claim_identity_digest_requires_work_authority() -> None:
    with pytest.raises(ValueError, match="WorkAuthority is required"):
        claim_identity_digest(object())  # type: ignore[arg-type]


def test_claim_identity_digest_ignores_plan_artifact_fields(tmp_path: Path) -> None:
    original = _authority(tmp_path, label="v1")
    revised = _authority(
        tmp_path,
        label="v2",
        mapped_openspec=("lifecycle", "lifecycle-appendix"),
        mapped_todo_paths=("docs/todo.md", "docs/todo-2.md"),
        source_revisions=("issue:14@open", "openspec:lifecycle@zzz"),
    )
    # 完整 digest 會因為 plan 產物欄位飄移而不同——這正是要繞過的部分。
    assert work_authority_digest(original) != work_authority_digest(revised)
    # 穩定 identity 不受影響。
    assert claim_identity_digest(original) == claim_identity_digest(revised)


def test_claim_identity_digest_still_reacts_to_genuine_identity_change(tmp_path: Path) -> None:
    original = _authority(tmp_path, label="v1")
    different_issue = _authority(tmp_path, label="other-issue", issues=(99,))
    assert claim_identity_digest(original) != claim_identity_digest(different_issue)


# --- AC2/AC3：plan review 前的修訂不觸發 supersede / 不變更 authority hash --


def test_plan_revision_before_review_does_not_supersede_or_change_claim_key(
    tmp_path: Path,
) -> None:
    original = _authority(tmp_path, label="v1")
    revised = _authority(
        tmp_path,
        label="v2",
        mapped_openspec=("lifecycle", "lifecycle-appendix"),
        mapped_todo_paths=("docs/todo.md", "docs/todo-2.md"),
        source_revisions=("issue:14@open", "openspec:lifecycle@zzz"),
    )
    candidate = _active_candidate(
        original=original, current=revised, active_plan_review_passed=False
    )
    original_key = candidate.active_claim_key

    manual = decide_manual_start(candidate, now_epoch=1_000)
    auto = decide_auto_claim(candidate, now_epoch=1_000)

    assert manual.action == "resume"
    assert manual.claim_key == original_key
    assert auto.action == "resume"
    assert auto.claim_key == original_key


def test_plan_revision_loop_v1_through_v4_never_grows_a_new_generation(
    tmp_path: Path,
) -> None:
    """hippo #18 第 3、7 條 regression：plan review 前反覆修訂不得產生 v3->v4 世代增長。"""

    original = _authority(tmp_path, label="v1")
    original_key = build_claim_key(_fresh_candidate(original))

    revisions = [
        _authority(
            tmp_path,
            label=f"v{n}",
            mapped_todo_paths=("docs/todo.md",) + tuple(f"docs/rev-{i}.md" for i in range(n)),
            source_revisions=("issue:14@open", f"openspec:lifecycle@rev-{n}"),
        )
        for n in range(2, 5)
    ]
    for revision in revisions:
        candidate = _active_candidate(
            original=original, current=revision, active_plan_review_passed=False
        )
        decision = decide_auto_claim(candidate, now_epoch=1_000)
        assert decision.action == "resume", "plan 修訂在 plan review 前不得脫離 resume"
        assert decision.claim_key == original_key, "authority 世代不得因 plan 修訂增長"


def test_without_the_guard_the_same_revision_would_have_superseded(tmp_path: Path) -> None:
    """對照組：若呼叫端誤把 active_plan_review_passed 設為 True（等同 pre-#213 行為），
    同一次 plan 修訂會被判定成 authority 變了，逼流程重新決策、生出新 claim_key
    ——這正是 hippo #18 v3->v4->... 世代增長的成因，用來證明本次 guard 確實生效。
    """

    original = _authority(tmp_path, label="v1")
    revised = _authority(
        tmp_path,
        label="v2",
        mapped_openspec=("lifecycle", "lifecycle-appendix"),
        mapped_todo_paths=("docs/todo.md", "docs/todo-2.md"),
        source_revisions=("issue:14@open", "openspec:lifecycle@zzz"),
    )
    candidate = _active_candidate(
        original=original, current=revised, active_plan_review_passed=True
    )
    decision = decide_auto_claim(candidate, now_epoch=1_000)
    assert decision.action == "claim"
    assert decision.claim_key != candidate.active_claim_key


# --- AC4：plan review 已通過（既有行為）不受影響 ----------------------------


def test_after_plan_review_passes_a_genuine_authority_change_still_forces_redecision(
    tmp_path: Path,
) -> None:
    original = _authority(tmp_path, label="v1")
    genuinely_different = _authority(tmp_path, label="other-issue", issues=(99,))
    candidate = replace(
        _active_candidate(
            original=original,
            current=genuinely_different,
            active_plan_review_passed=True,
        ),
        confirmed_issue=99,
    )
    decision = decide_auto_claim(candidate, now_epoch=1_000)
    assert decision.action in {"claim", "needs_human"}
    if decision.action == "claim":
        assert decision.claim_key != candidate.active_claim_key


def test_active_plan_review_passed_defaults_true_and_preserves_existing_behaviour(
    tmp_path: Path,
) -> None:
    authority = _authority(tmp_path, label="v1")
    candidate = _fresh_candidate(authority)
    assert candidate.active_plan_review_passed is True
    assert candidate.active_claim_identity_digest is None
    assert decide_manual_start(candidate, now_epoch=1_000).action == "claim"


# --- 驗證：欄位型別與必要性 --------------------------------------------------


def test_active_plan_review_passed_must_be_boolean(tmp_path: Path) -> None:
    authority = _authority(tmp_path, label="v1")
    candidate = _active_candidate(
        original=authority, current=authority, active_plan_review_passed=True
    )
    with pytest.raises(ValueError, match="must be boolean"):
        decide_auto_claim(
            replace(candidate, active_plan_review_passed="yes"),  # type: ignore[arg-type]
            now_epoch=1_000,
        )


def test_pre_freeze_active_claim_identity_digest_is_required(tmp_path: Path) -> None:
    authority = _authority(tmp_path, label="v1")
    candidate = _active_candidate(
        original=authority, current=authority, active_plan_review_passed=False
    )
    with pytest.raises(ValueError, match="pre-freeze identity digest"):
        decide_auto_claim(
            replace(candidate, active_claim_identity_digest=None),
            now_epoch=1_000,
        )
    with pytest.raises(ValueError, match="pre-freeze identity digest"):
        decide_auto_claim(
            replace(candidate, active_claim_identity_digest="not-a-hash"),
            now_epoch=1_000,
        )
