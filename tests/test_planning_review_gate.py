"""#212：plan_review_gate() 三項判定（#208 設計 A.1 第 3 點，不含 freeze 位移）。

驗收條件對應：
1. 完整性：plan 為每個 acceptance surface 備有對應 task
2. 契約相容性：plan scope 與 R-09/R-16/R-19/R-22 相容（hippo #18 第 9 條在此攔截）
3. 封套相符：plan 宣告的 invariant_count/artifact_classes 落在指定 builder 封套內；
   builder 無封套資料時記 envelope_unavailable 並以可觀測 bypass 通過（對齊 #202 定案）
4. 三項任一不過即 fail closed（ready=False），policy-scope-conflict 為 terminal，其餘可重試
"""

from __future__ import annotations

import pytest

from paulsha_cortex.coordinator.planning import (
    PlanningArtifact,
    PlanReviewOutcome,
    plan_review_gate,
)


def _plan_text(
    *,
    invariant_count: object = 1,
    artifact_classes: str = "[code, test]",
    scope_excludes: str | None = None,
    tasks_body: str = (
        "- 實作 code 變動\n"
        "- 補 test 覆蓋\n"
        "- 更新 changelog fragment\n"
        "- 同步 CLI 說明\n"
        "- 補 docs 段落\n"
    ),
    status: str = "accepted",
) -> str:
    excludes_line = f"scope_excludes: {scope_excludes}\n" if scope_excludes is not None else ""
    return (
        "---\n"
        f"invariant_count: {invariant_count}\n"
        f"artifact_classes: {artifact_classes}\n"
        f"{excludes_line}"
        f"status: {status}\n"
        "---\n"
        "## Tasks\n"
        f"{tasks_body}"
    )


def _plan_artifact(**kwargs: object) -> PlanningArtifact:
    return PlanningArtifact(kind="plan", ref="docs/superpowers/plans/demo.md", text=_plan_text(**kwargs))


ALL_SURFACES = frozenset({"code", "test"})
ALL_RULES = frozenset({"R-09", "R-16", "R-19", "R-22"})


def test_gate_ready_when_all_three_checks_pass():
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(),
        acceptance_surfaces=ALL_SURFACES,
        applicable_contract_rules=ALL_RULES,
    )
    assert isinstance(outcome, PlanReviewOutcome)
    assert outcome.ready is True
    assert outcome.failed_check is None
    assert outcome.terminal is False
    assert outcome.checks_run == ("completeness", "contract_compatibility", "envelope")


# --- 驗收條件 1：完整性 -------------------------------------------------


def test_completeness_fails_when_acceptance_surface_has_no_task():
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(tasks_body="- 實作 code 變動\n"),
        acceptance_surfaces=frozenset({"code", "docs"}),
        applicable_contract_rules=frozenset(),
    )
    assert outcome.ready is False
    assert outcome.failed_check == "completeness"
    assert outcome.terminal is False
    assert outcome.checks_run == ("completeness",)


def test_completeness_passes_with_empty_acceptance_surfaces():
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(tasks_body="- 無關項目\n"),
        acceptance_surfaces=frozenset(),
        applicable_contract_rules=frozenset(),
    )
    assert outcome.ready is True


def test_completeness_matches_task_text_case_insensitively():
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(tasks_body="- 補 CODE 變動與 TEST 覆蓋\n"),
        acceptance_surfaces=frozenset({"code", "test"}),
        applicable_contract_rules=frozenset(),
    )
    assert outcome.ready is True


# --- 驗收條件 2：契約相容性 ----------------------------------------------


def test_contract_compatibility_fails_when_required_task_missing():
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(tasks_body="- 只做 code 變動\n"),
        acceptance_surfaces=frozenset(),
        applicable_contract_rules=frozenset({"R-19"}),
    )
    assert outcome.ready is False
    assert outcome.failed_check == "contract_compatibility"
    assert outcome.terminal is False


def test_contract_compatibility_passes_when_rule_keyword_present():
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(tasks_body="- 補測試（test）覆蓋新行為\n"),
        acceptance_surfaces=frozenset(),
        applicable_contract_rules=frozenset({"R-19"}),
    )
    assert outcome.ready is True


def test_contract_compatibility_is_terminal_on_explicit_scope_conflict():
    # hippo #18 第 9 條：plan 明確排除 changelog，但 R-09 要求 changelog fragment。
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(
            scope_excludes="[changelog]",
            tasks_body="- 只做 code 變動\n",
        ),
        acceptance_surfaces=frozenset(),
        applicable_contract_rules=frozenset({"R-09"}),
    )
    assert outcome.ready is False
    assert outcome.failed_check == "contract_compatibility"
    assert outcome.terminal is True
    assert outcome.reason is not None and "policy-scope-conflict" in outcome.reason


def test_contract_compatibility_rejects_unknown_rule():
    with pytest.raises(ValueError, match="R-99"):
        plan_review_gate(
            plan_artifact=_plan_artifact(),
            acceptance_surfaces=frozenset(),
            applicable_contract_rules=frozenset({"R-99"}),
        )


# --- 驗收條件 3：封套相符 ------------------------------------------------


def test_envelope_bypasses_when_lookup_is_none():
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(invariant_count=99, artifact_classes="[code, test, exotic]"),
        acceptance_surfaces=frozenset(),
        applicable_contract_rules=frozenset(),
        envelope_lookup=None,
    )
    assert outcome.ready is True
    assert outcome.observations["envelope"]["bypass"] == "envelope_unavailable"


def test_envelope_bypasses_when_lookup_returns_none():
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(),
        acceptance_surfaces=frozenset(),
        applicable_contract_rules=frozenset(),
        envelope_lookup=lambda: None,
    )
    assert outcome.ready is True
    assert outcome.observations["envelope"]["bypass"] == "envelope_unavailable"


def test_envelope_fails_closed_when_invariant_count_exceeds_envelope():
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(invariant_count=5, artifact_classes="[code]"),
        acceptance_surfaces=frozenset(),
        applicable_contract_rules=frozenset(),
        envelope_lookup=lambda: {"invariant_count": 2, "artifact_classes": ["code", "test"]},
    )
    assert outcome.ready is False
    assert outcome.failed_check == "envelope"
    assert outcome.terminal is False


def test_envelope_fails_closed_when_artifact_class_exceeds_envelope():
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(invariant_count=1, artifact_classes="[code, exotic]"),
        acceptance_surfaces=frozenset(),
        applicable_contract_rules=frozenset(),
        envelope_lookup=lambda: {"invariant_count": 2, "artifact_classes": ["code", "test"]},
    )
    assert outcome.ready is False
    assert outcome.failed_check == "envelope"


def test_envelope_passes_when_within_bounds():
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(invariant_count=2, artifact_classes="[code]"),
        acceptance_surfaces=frozenset(),
        applicable_contract_rules=frozenset(),
        envelope_lookup=lambda: {"invariant_count": 2, "artifact_classes": ["code", "test"]},
    )
    assert outcome.ready is True


def test_missing_invariant_count_declaration_rejected():
    text = (
        "---\n"
        "artifact_classes: [code]\n"
        "status: accepted\n"
        "---\n"
        "## Tasks\n"
        "- a\n"
    )
    artifact = PlanningArtifact(kind="plan", ref="docs/superpowers/plans/demo.md", text=text)
    with pytest.raises(ValueError, match="invariant_count"):
        plan_review_gate(
            plan_artifact=artifact,
            acceptance_surfaces=frozenset(),
            applicable_contract_rules=frozenset(),
        )


def test_missing_artifact_classes_declaration_rejected():
    text = (
        "---\n"
        "invariant_count: 1\n"
        "status: accepted\n"
        "---\n"
        "## Tasks\n"
        "- a\n"
    )
    artifact = PlanningArtifact(kind="plan", ref="docs/superpowers/plans/demo.md", text=text)
    with pytest.raises(ValueError, match="artifact_classes"):
        plan_review_gate(
            plan_artifact=artifact,
            acceptance_surfaces=frozenset(),
            applicable_contract_rules=frozenset(),
        )


# --- 檢查次序（cost order：completeness → contract_compatibility → envelope）----


def test_checks_short_circuit_on_first_failure_completeness_then_contract():
    outcome = plan_review_gate(
        plan_artifact=_plan_artifact(tasks_body="- 無關項目\n"),
        acceptance_surfaces=frozenset({"code"}),
        applicable_contract_rules=frozenset({"R-19"}),
    )
    assert outcome.failed_check == "completeness"
    assert outcome.checks_run == ("completeness",)


# --- 非 plan artifact kind ------------------------------------------------


def test_non_plan_artifact_kind_rejected():
    artifact = PlanningArtifact(kind="design", ref="docs/superpowers/specs/demo-design.md", text="---\n---\n")
    with pytest.raises(ValueError, match="plan"):
        plan_review_gate(
            plan_artifact=artifact,
            acceptance_surfaces=frozenset(),
            applicable_contract_rules=frozenset(),
        )
