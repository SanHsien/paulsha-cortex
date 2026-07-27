"""#222（design #208 H.2）：sizing_score／sizing_band 寫入 work item（WorkflowRun）。

驗收條件 3：每次 repair／re-claim 後重算 band，不得沿用 claim 當時判定——這裡
驗證 registry 的 _manager_create_workflow_run／_manager_update_workflow_run
機制本身支援每次覆寫成新算出的值（呼叫端每次都要重新傳入，不會被悄悄沿用舊
band），而非把 claim 當時的判定當成永久快照。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from paulsha_cortex.coordinator.registry import JobRegistry
from paulsha_cortex.coordinator.workflow import WorkflowStep


def _step(phase: str = "plan") -> WorkflowStep:
    return WorkflowStep(
        phase=phase,
        persona="planner" if phase == "plan" else "builder",
        card="writing-plans" if phase == "plan" else "test-driven-development",
        executor="agy",
        model="gemini-3.1-pro-high",
        domain="google",
        inputs=(),
        outputs=(),
        gate_result="pending",
    )


def _create_run(registry: JobRegistry, **overrides: object):
    fields: dict[str, object] = {
        "work_id": "sizing-band-work",
        "repo": "hamanpaul/paulsha-cortex",
        "claim_key": "claim:v1:" + "a" * 64,
        "source_revision": "rev-a",
        "workspace_root": "/tmp/paulsha-cortex",
        "combo": "feature-oneshot",
        "current_phase": "plan",
        "steps": (_step(),),
    }
    fields.update(overrides)
    return registry._manager_create_workflow_run(**fields)


def test_create_workflow_run_persists_initial_sizing_snapshot(tmp_path: Path) -> None:
    state = tmp_path / "jobs.json"
    registry = JobRegistry(state_path=state)
    created = _create_run(registry, sizing_score=8, sizing_band="red")

    assert created.sizing_score == 8
    assert created.sizing_band == "red"
    reloaded = JobRegistry(state_path=state)
    assert reloaded.get_workflow_run(created.run_id).sizing_score == 8
    assert reloaded.get_workflow_run(created.run_id).sizing_band == "red"


def test_update_after_repair_recomputes_band_and_does_not_keep_claim_time_value(
    tmp_path: Path,
) -> None:
    state = tmp_path / "jobs.json"
    registry = JobRegistry(state_path=state)
    created = _create_run(registry, sizing_score=8, sizing_band="red")

    # 模擬 repair 後重算：分數大幅下降，band 從 red 掉到 green。
    repaired = registry._manager_update_workflow_run(
        created.run_id,
        current_phase="build",
        sizing_score=2,
        sizing_band="green",
    )
    assert repaired.sizing_score == 2
    assert repaired.sizing_band == "green"
    # 不得殘留 claim 當時的 red 判定。
    assert repaired.sizing_score != created.sizing_score
    assert repaired.sizing_band != created.sizing_band

    persisted = JobRegistry(state_path=state).get_workflow_run(created.run_id)
    assert persisted.sizing_score == 2
    assert persisted.sizing_band == "green"


def test_update_without_sizing_args_carries_forward_last_recorded_snapshot(
    tmp_path: Path,
) -> None:
    state = tmp_path / "jobs.json"
    registry = JobRegistry(state_path=state)
    created = _create_run(registry, sizing_score=5, sizing_band="yellow")

    unrelated_update = registry._manager_update_workflow_run(
        created.run_id,
        current_phase="build",
    )
    assert unrelated_update.sizing_score == 5
    assert unrelated_update.sizing_band == "yellow"


def test_mismatched_score_and_band_pair_rejected_on_create(tmp_path: Path) -> None:
    state = tmp_path / "jobs.json"
    registry = JobRegistry(state_path=state)
    with pytest.raises(ValueError):
        _create_run(registry, sizing_score=8, sizing_band="green")


def test_mismatched_score_and_band_pair_rejected_on_update(tmp_path: Path) -> None:
    state = tmp_path / "jobs.json"
    registry = JobRegistry(state_path=state)
    created = _create_run(registry, sizing_score=1, sizing_band="green")
    with pytest.raises(ValueError):
        registry._manager_update_workflow_run(
            created.run_id,
            current_phase="build",
            sizing_score=9,
            sizing_band="green",
        )
