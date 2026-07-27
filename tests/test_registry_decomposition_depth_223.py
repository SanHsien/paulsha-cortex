"""#223（design #208 H.3）：decomposition_depth 寫入/更新 work item（WorkflowRun）。

比照 #222 sizing_score/sizing_band 的 registry 測試模式：create 支援初值、
update 支援覆寫與「未傳入時沿用上次快照」兩種情境。
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
        "work_id": "decomposition-depth-work",
        "repo": "hamanpaul/paulsha-cortex",
        "claim_key": "claim:v1:" + "b" * 64,
        "source_revision": "rev-a",
        "workspace_root": "/tmp/paulsha-cortex",
        "combo": "feature-oneshot",
        "current_phase": "plan",
        "steps": (_step(),),
    }
    fields.update(overrides)
    return registry._manager_create_workflow_run(**fields)


def test_create_workflow_run_defaults_decomposition_depth_to_zero(tmp_path: Path) -> None:
    state = tmp_path / "jobs.json"
    registry = JobRegistry(state_path=state)
    created = _create_run(registry)
    assert created.decomposition_depth == 0


def test_create_workflow_run_persists_child_decomposition_depth(tmp_path: Path) -> None:
    state = tmp_path / "jobs.json"
    registry = JobRegistry(state_path=state)
    created = _create_run(registry, decomposition_depth=1)

    assert created.decomposition_depth == 1
    reloaded = JobRegistry(state_path=state)
    assert reloaded.get_workflow_run(created.run_id).decomposition_depth == 1


def test_update_can_overwrite_decomposition_depth(tmp_path: Path) -> None:
    state = tmp_path / "jobs.json"
    registry = JobRegistry(state_path=state)
    created = _create_run(registry)

    updated = registry._manager_update_workflow_run(
        created.run_id,
        decomposition_depth=2,
    )
    assert updated.decomposition_depth == 2
    persisted = JobRegistry(state_path=state).get_workflow_run(created.run_id)
    assert persisted.decomposition_depth == 2


def test_update_without_depth_arg_carries_forward_last_recorded_snapshot(
    tmp_path: Path,
) -> None:
    state = tmp_path / "jobs.json"
    registry = JobRegistry(state_path=state)
    created = _create_run(registry, decomposition_depth=1)

    unrelated_update = registry._manager_update_workflow_run(
        created.run_id,
        current_phase="build",
    )
    assert unrelated_update.decomposition_depth == 1


def test_depth_above_limit_rejected_on_create(tmp_path: Path) -> None:
    state = tmp_path / "jobs.json"
    registry = JobRegistry(state_path=state)
    with pytest.raises(ValueError):
        _create_run(registry, decomposition_depth=3)
