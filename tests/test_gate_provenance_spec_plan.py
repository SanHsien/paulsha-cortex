"""#379：builder 完成回報與實際驗收背離——gate 清單來源改由 spec/plan 導出。

Root cause（見 #379 2026-08-10 複驗 comment）：#261 的 gate ledger cross-check
（``terminal_contract.authorize_terminal``）只對照「builder 自報的 gate_evidence」
與「manager 重跑的 ledger」，但 ledger 本身的 gate 集合完全由 operator 的
``PSC_GATE_CMD_*`` env 決定，與 spec/plan 的驗收條件（deck 卡片的
``test_policy``）沒有機械連結。operator 若漏宣告某個 plan 要求的 gate，
builder 自報的「超集」項目就落在 ledger 之外，#308 的空/局部 ledger 又直接
放行，形成無人驗證的落差。

本檔驗證三項改動：
1. gate 清單來源改由 plan 導出（``WorkflowStep.test_policy`` → 應驗 gate 名稱）。
2. 空/局部 ledger 若遺漏 plan 宣告的應驗 gate → fail closed（needs_human），
   而非 #308 的 vacuous pass；純無 gate 宣告的卡片（test_policy=none）維持
   既有的合法空 ledger 放行語意。
3. 驗收判準（test_policy）於派工當下 pin 進 job，harvest 時與 registry 現值
   比對，任何 drift 都 fail closed（比照既有 ``_review_inputs_drifted``／
   ``_pinned_input_mismatches`` pinned-input 機制）。

另附一個獨立於 #379 描述之外、但複驗過程中發現、且會讓上述第 1 項落空的
既有 bug 回歸測試：``_audit_phase_steps`` 在任何一次 phase advance 時，會把
*全部* step（不只是被更新的那個）的 ``test_policy``／``skill_ref``／``action``／
``commit_policy`` 重置為 ``None``——即使該 step 完全不在本次更新的 phase／
card 範圍內。這代表在真正走過 ``apply_workflow_action(action="advance")`` 的
production 路徑中，build phase 卡片的 ``test_policy`` 在真正被拿來跑之前就已
經被抹除，本票要接的「gate 來源改由 plan 導出」機制會因此變成 dead code。
"""

from __future__ import annotations

import json
from dataclasses import replace as _replace
from pathlib import Path

import pytest

from paulsha_cortex.coordinator import manager
from paulsha_cortex.coordinator import terminal_contract as tc
from paulsha_cortex.coordinator.registry import JobRegistry
from paulsha_cortex.coordinator.workflow import WorkflowStep


# --------------------------------------------------------------------------
# 0) 既有 bug：_audit_phase_steps 抹除未涉及 step 的 test_policy 等欄位
# --------------------------------------------------------------------------


def test_audit_phase_steps_preserves_untouched_step_fields() -> None:
    """RED（修復前）：_audit_phase_steps 只該更新落在 (phase, card_id) 範圍內的
    step 的 executor/model/domain/outputs/gate_result；其餘欄位（含未命中的
    step 本身的 skill_ref/action/commit_policy/test_policy）必須原樣保留。"""

    build_step = WorkflowStep(
        phase="build",
        persona="builder",
        card="tdd-red",
        executor=None,
        model=None,
        domain=None,
        inputs=(),
        outputs=(),
        gate_result="pending",
        skill_ref="superpowers:test-driven-development",
        action="new RED regression test",
        commit_policy="required",
        test_policy="red-required",
    )
    unrelated_step = WorkflowStep(
        phase="define",
        persona="planner",
        card="brainstorming",
        executor=None,
        model=None,
        domain=None,
        inputs=(),
        outputs=(),
        gate_result="passed",
        skill_ref="superpowers:brainstorming",
        action=None,
        commit_policy=None,
        test_policy=None,
    )

    # 模擬 define phase 的卡片先行 advance——與 build_step 完全無關的
    # (phase, card_id) 組合。
    audited = manager._audit_phase_steps(
        (unrelated_step, build_step),
        phase="define",
        executor="codex",
        model="planner-model",
        domain="openai",
        outputs=(),
        card_id="brainstorming",
    )
    audited_build_step = next(step for step in audited if step.card == "tdd-red")
    assert audited_build_step.test_policy == "red-required"
    assert audited_build_step.skill_ref == "superpowers:test-driven-development"
    assert audited_build_step.action == "new RED regression test"
    assert audited_build_step.commit_policy == "required"


# --------------------------------------------------------------------------
# 1) 應驗 gate 名稱由 test_policy 導出
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "test_policy,expected",
    [
        (None, frozenset()),
        ("none", frozenset()),
        ("red-required", frozenset({"pytest"})),
        ("focused", frozenset({"pytest"})),
        ("full", frozenset({"pytest"})),
    ],
)
def test_expected_gate_names_for_test_policy(test_policy, expected) -> None:
    assert manager._expected_gate_names_for_test_policy(test_policy) == expected


# --------------------------------------------------------------------------
# 2) authorize_terminal：spec/plan 應驗 gate 缺席 → fail closed
# --------------------------------------------------------------------------


def _passed_envelope(gate_evidence: list[dict[str, object]] | None = None) -> tc.TerminalEnvelope:
    return tc.validate_envelope(
        {
            "schema_version": tc.TERMINAL_SCHEMA_VERSION,
            "kind": "workflow-card",
            "status": "passed",
            "run_id": "run",
            "card_id": "card",
            "candidate": "a" * 40,
            "outputs": [],
            "diagnostics": {},
            "gate_evidence": gate_evidence or [],
        }
    )


def _write_ledger(tmp_path: Path, name: str, *, gates: list[dict[str, object]]) -> Path:
    ledger_path = tmp_path / f"{name}.gates.json"
    payload = {
        "schema_version": tc.GATE_LEDGER_SCHEMA_VERSION,
        "kind": tc.GATE_LEDGER_KIND,
        "slice_id": "slice",
        "gates": gates,
    }
    ledger_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return ledger_path


def test_empty_ledger_with_expected_gate_fails_closed(tmp_path: Path) -> None:
    """RED→GREEN 核心：#308 的空 ledger vacuous pass 不得適用在 plan 宣告了
    應驗 gate 的情境——差集必須有人驗，不能無聲放行。"""

    ledger_path = _write_ledger(tmp_path, "empty", gates=[])
    envelope = _passed_envelope()
    with pytest.raises(tc.TerminalContractError) as excinfo:
        tc.authorize_terminal(
            envelope,
            ledger_path=ledger_path,
            require_ledger=True,
            expected_gate_names=frozenset({"pytest"}),
        )
    assert excinfo.value.reason == "gate-ledger-missing-expected-gate"
    assert "pytest" in str(excinfo.value)


def test_partial_ledger_missing_expected_gate_fails_closed(tmp_path: Path) -> None:
    """superset 差集：operator 的 PSC_GATE_CMD_* 只宣告了 openspec，沒宣告 plan
    要求的 pytest；ledger 非空但缺該項，仍須 fail closed。"""

    ledger_path = _write_ledger(
        tmp_path, "partial", gates=[{"name": "openspec", "status": "passed", "exit_code": 0}]
    )
    envelope = _passed_envelope()
    with pytest.raises(tc.TerminalContractError) as excinfo:
        tc.authorize_terminal(
            envelope,
            ledger_path=ledger_path,
            require_ledger=True,
            expected_gate_names=frozenset({"pytest"}),
        )
    assert excinfo.value.reason == "gate-ledger-missing-expected-gate"


def test_empty_ledger_without_expected_gates_still_authorized(tmp_path: Path) -> None:
    """對稱正向案例：純無 gate 宣告的 slice（expected_gate_names 為空，例如
    test_policy=none 的卡片）維持 #308 既有的合法空 ledger 放行語意。"""

    ledger_path = _write_ledger(tmp_path, "empty-no-expect", gates=[])
    envelope = _passed_envelope()
    authorization = tc.authorize_terminal(
        envelope,
        ledger_path=ledger_path,
        require_ledger=True,
        expected_gate_names=frozenset(),
    )
    assert authorization.authorized is True


def test_expected_gate_present_and_passed_is_authorized(tmp_path: Path) -> None:
    ledger_path = _write_ledger(
        tmp_path, "satisfied", gates=[{"name": "pytest", "status": "passed", "exit_code": 0}]
    )
    envelope = _passed_envelope([{"name": "pytest", "status": "passed"}])
    authorization = tc.authorize_terminal(
        envelope,
        ledger_path=ledger_path,
        require_ledger=True,
        expected_gate_names=frozenset({"pytest"}),
    )
    assert authorization.authorized is True
    assert "pytest" in authorization.verified_gates


def test_authorize_terminal_default_expected_gate_names_is_backward_compatible(
    tmp_path: Path,
) -> None:
    """未帶新參數的既有呼叫端行為不變：預設 expected_gate_names 為空集合，
    空 ledger 仍走 #308 既有的 vacuous pass。"""

    ledger_path = _write_ledger(tmp_path, "legacy-call", gates=[])
    envelope = _passed_envelope([{"name": "pwd", "status": "passed"}])
    authorization = tc.authorize_terminal(envelope, ledger_path=ledger_path, require_ledger=True)
    assert authorization.authorized is True


# --------------------------------------------------------------------------
# 3) 端到端：terminalize_workflow_job 走真實 compiled WorkflowRun
# --------------------------------------------------------------------------


def _compiled_step_run(registry, tmp_path: Path, *, task: str, change: str):
    from paulsha_cortex.deck.compile import compile_combo
    from paulsha_cortex.deck.schema import (
        DEFAULT_CARDS_PATH,
        DEFAULT_COMBOS_DIR,
        load_cards,
        load_combo,
    )

    cards = load_cards(DEFAULT_CARDS_PATH)
    combo = load_combo(DEFAULT_COMBOS_DIR / "feature-oneshot.yaml", cards)
    manifest = compile_combo(combo, cards, task, change=change).workflow_manifest
    assert manifest is not None
    run = registry._manager_create_workflow_run(
        work_id=change,
        repo="hamanpaul/paulsha-cortex",
        claim_key="claim:v1:" + "3" * 64,
        source_revision="4" * 64,
        workspace_root=str(tmp_path),
        combo="feature-oneshot",
        current_phase="build",
        steps=tuple(
            _replace(step, executor="codex", model="gpt-primary", domain="openai")
            for step in manifest.steps
        ),
        issue_refs=(),
        openspec_refs=(),
        pr_refs=(),
        attempts={},
        facets=(),
        gate_status="running",
    )
    return run


def _terminal_log(tmp_path: Path, *, name: str, run_id: str, card_id: str) -> Path:
    log = tmp_path / f"{name}.jsonl"
    log.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "workflow-card",
                "status": "passed",
                "run_id": run_id,
                "card_id": card_id,
                "candidate": "a" * 40,
                "outputs": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return log


def _write_manager_ledger(log_path: Path, *, gates: list[dict[str, object]]) -> None:
    ledger_path = tc.gate_ledger_path(log_path)
    payload = {
        "schema_version": tc.GATE_LEDGER_SCHEMA_VERSION,
        "kind": tc.GATE_LEDGER_KIND,
        "slice_id": "slice",
        "gates": gates,
    }
    ledger_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_manager_harvest_fails_closed_when_plan_requires_gate_but_ledger_empty(
    tmp_path: Path,
) -> None:
    """核心回歸：tdd-red 卡（test_policy=red-required，機械要求 pytest gate）
    + operator 完全沒宣告 PSC_GATE_CMD_*（空 ledger）+ builder 自稱 passed
    → terminalize_workflow_job 必須 fail closed，不得沿用 #308 的 vacuous pass。
    """

    registry = JobRegistry(state_path=tmp_path / "registry.json")
    run = _compiled_step_run(
        registry, tmp_path, task="gate provenance red", change="gate-provenance-red"
    )
    step = next(item for item in run.steps if item.card == "tdd-red")
    assert step.test_policy == "red-required"

    log = _terminal_log(tmp_path, name="build", run_id=run.run_id, card_id=step.card)
    _write_manager_ledger(log, gates=[])
    job = registry.create_job(
        task="build",
        persona="builder",
        branch="feature/work",
        pane="",
        worktree=str(tmp_path),
        executor="codex",
        model_id="builder",
        independence_domain="openai",
        subject_head="d" * 40,
        workflow_run_id=run.run_id,
        workflow_claim_key=run.claim_key,
        workflow_repo=run.repo,
        workflow_card=step.card,
        workflow_phase="build",
        workflow_repo_root=str(tmp_path),
        workflow_outputs=step.outputs,
        source_revision="rev",
    )
    registry.attach_launch_handle(job["job_id"], log_path=str(log))
    registry.update_headless_result(job["job_id"], status="exited", exit_code=0)

    with pytest.raises(tc.TerminalContractError) as excinfo:
        manager.terminalize_workflow_job(
            registry, job_id=job["job_id"], coordinator_root=tmp_path
        )
    assert excinfo.value.reason == "gate-ledger-missing-expected-gate"
    assert registry.get_job(job["job_id"])["workflow_evidence"] is None


def test_manager_harvest_passes_when_no_gate_declared_by_plan_and_ledger_empty(
    tmp_path: Path,
) -> None:
    """對照組：worktree-isolation 卡（test_policy=none）本就不要求任何 gate，
    空 ledger 仍須正常通過——證明本次改動沒有連坐無辜的「純無 gate 宣告」情境。
    """

    registry = JobRegistry(state_path=tmp_path / "registry.json")
    run = _compiled_step_run(
        registry, tmp_path, task="gate provenance none", change="gate-provenance-none"
    )
    docs_step = next(item for item in run.steps if item.card == "worktree-isolation")
    assert docs_step.test_policy in (None, "none")

    log = _terminal_log(tmp_path, name="build-none", run_id=run.run_id, card_id=docs_step.card)
    _write_manager_ledger(log, gates=[])
    job = registry.create_job(
        task="build-none",
        persona="builder",
        branch="feature/work-none",
        pane="",
        worktree=str(tmp_path),
        executor="codex",
        model_id="builder",
        independence_domain="openai",
        subject_head="d" * 40,
        workflow_run_id=run.run_id,
        workflow_claim_key=run.claim_key,
        workflow_repo=run.repo,
        workflow_card=docs_step.card,
        workflow_phase="build",
        workflow_repo_root=str(tmp_path),
        workflow_outputs=docs_step.outputs,
        source_revision="rev",
    )
    registry.attach_launch_handle(job["job_id"], log_path=str(log))
    registry.update_headless_result(job["job_id"], status="exited", exit_code=0)

    terminal = manager.terminalize_workflow_job(
        registry, job_id=job["job_id"], coordinator_root=tmp_path
    )
    assert terminal["workflow_evidence"] is not None


# --------------------------------------------------------------------------
# 4) 驗收判準（test_policy）pinned input：派工時 pin，harvest 時比對 drift
# --------------------------------------------------------------------------


def test_create_job_stores_pinned_workflow_test_policy(tmp_path: Path) -> None:
    registry = JobRegistry(state_path=tmp_path / "registry.json")
    job = registry.create_job(
        task="pin-check",
        persona="builder",
        branch="feature/pin-check",
        pane="",
        worktree=str(tmp_path),
        workflow_run_id="run",
        workflow_claim_key="claim",
        workflow_repo="owner/repo",
        workflow_card="tdd-red",
        workflow_phase="build",
        workflow_test_policy="red-required",
    )
    assert job["workflow_test_policy"] == "red-required"
    assert registry.get_job(job["job_id"])["workflow_test_policy"] == "red-required"


def test_manager_harvest_fails_closed_when_acceptance_definition_drifted(tmp_path: Path) -> None:
    """builder 動到（或任何行程動到）pinned 的驗收判準：job 派工時 pin 的
    test_policy 與 registry 現有的 run.steps test_policy 不一致 → 必須被當成
    input drift mismatch fail closed，不得沿用新值讓自報靜默通過。"""

    registry = JobRegistry(state_path=tmp_path / "registry.json")
    run = _compiled_step_run(
        registry, tmp_path, task="gate provenance drift", change="gate-provenance-drift"
    )
    step = next(item for item in run.steps if item.card == "tdd-red")
    assert step.test_policy == "red-required"

    log = _terminal_log(tmp_path, name="build-drift", run_id=run.run_id, card_id=step.card)
    # ledger 全綠通過：若沒有 drift 保護，這份 ledger 加上（已被弱化的）
    # test_policy=None 會讓 harvest 直接放行。
    _write_manager_ledger(log, gates=[{"name": "pytest", "status": "passed", "exit_code": 0}])
    job = registry.create_job(
        task="build-drift",
        persona="builder",
        branch="feature/work-drift",
        pane="",
        worktree=str(tmp_path),
        executor="codex",
        model_id="builder",
        independence_domain="openai",
        subject_head="d" * 40,
        workflow_run_id=run.run_id,
        workflow_claim_key=run.claim_key,
        workflow_repo=run.repo,
        workflow_card=step.card,
        workflow_phase="build",
        workflow_repo_root=str(tmp_path),
        workflow_outputs=step.outputs,
        source_revision="rev",
        workflow_test_policy=step.test_policy,
    )
    registry.attach_launch_handle(job["job_id"], log_path=str(log))
    registry.update_headless_result(job["job_id"], status="exited", exit_code=0)

    # 模擬派工後、harvest 前，run.steps 的驗收判準已經變動（無論肇因是 bug 還
    # 是被動到）——tdd-red 卡的 test_policy 被弱化成 None。
    drifted_steps = tuple(
        _replace(item, test_policy=None) if item.card == step.card else item
        for item in run.steps
    )
    registry._manager_update_workflow_run(run.run_id, steps=drifted_steps)

    with pytest.raises(tc.TerminalContractError) as excinfo:
        manager.terminalize_workflow_job(
            registry, job_id=job["job_id"], coordinator_root=tmp_path
        )
    assert excinfo.value.reason == "workflow-acceptance-definition-drift"
    assert registry.get_job(job["job_id"])["workflow_evidence"] is None


def test_manager_harvest_unaffected_when_job_has_no_pinned_test_policy(tmp_path: Path) -> None:
    """回溯相容：既有（或測試建構）的 job 沒有 workflow_test_policy 欄位時
    （legacy 資料／未經真正派工路徑建立的 job），不觸發 drift fail closed，
    仍走一般 expected-gate 檢查——不得因為新增此保護而誤殺舊資料。"""

    registry = JobRegistry(state_path=tmp_path / "registry.json")
    run = _compiled_step_run(
        registry, tmp_path, task="gate provenance no pin", change="gate-provenance-no-pin"
    )
    step = next(item for item in run.steps if item.card == "tdd-red")
    assert step.test_policy == "red-required"

    log = _terminal_log(tmp_path, name="build-no-pin", run_id=run.run_id, card_id=step.card)
    _write_manager_ledger(
        log, gates=[{"name": "pytest", "status": "failed", "exit_code": 1, "detail": "1 failed"}]
    )
    job = registry.create_job(
        task="build-no-pin",
        persona="builder",
        branch="feature/work-no-pin",
        pane="",
        worktree=str(tmp_path),
        executor="codex",
        model_id="builder",
        independence_domain="openai",
        subject_head="d" * 40,
        workflow_run_id=run.run_id,
        workflow_claim_key=run.claim_key,
        workflow_repo=run.repo,
        workflow_card=step.card,
        workflow_phase="build",
        workflow_repo_root=str(tmp_path),
        workflow_outputs=step.outputs,
        source_revision="rev",
        # 刻意不帶 workflow_test_policy（模擬 legacy job）。
    )
    registry.attach_launch_handle(job["job_id"], log_path=str(log))
    registry.update_headless_result(job["job_id"], status="exited", exit_code=0)

    # red-required 語意反轉：pytest exit_code=1 視為合格 RED，應該正常通過。
    terminal = manager.terminalize_workflow_job(
        registry, job_id=job["job_id"], coordinator_root=tmp_path
    )
    assert terminal["workflow_evidence"] is not None
