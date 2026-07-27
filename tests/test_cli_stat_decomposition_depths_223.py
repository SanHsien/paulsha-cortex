"""#223（design #208 H.3）：decomposition_depth 進可觀測面——
``cortex stat --decomposition-depths`` 依拆分深度彙總 workflow runs。

比照 #208 既有 ``--retry-classifications`` 彙總面的測試模式（見
tests/test_work_actions_retry_invalidation.py）。
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from paulsha_cortex.coordinator import cli as coordinator_cli
from paulsha_cortex.coordinator.registry import JobRegistry
from paulsha_cortex.coordinator.workflow import WorkflowStep


def _step() -> WorkflowStep:
    return WorkflowStep(
        phase="build",
        persona="builder",
        card="subagent-build",
        executor="agy",
        model="gemini-3.1-pro-high",
        domain="google",
        inputs=(),
        outputs=(),
        gate_result="pending",
    )


def test_stat_decomposition_depths_aggregates_workflow_runs(tmp_path: Path) -> None:
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    for idx, depth in enumerate([0, 0, 1, 2]):
        registry._manager_create_workflow_run(
            repo="hamanpaul/paulsha-cortex",
            work_id=f"agg-depth-{idx}",
            claim_key=f"claim:v1:{str(idx) * 64}",
            source_revision="rev-agg-depth",
            workspace_root="/tmp/workspace",
            combo="feature-oneshot",
            current_phase="build",
            steps=(_step(),),
            issue_refs=(f"hamanpaul/paulsha-cortex#{910 + idx}",),
            decomposition_depth=depth,
        )

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = coordinator_cli.main(
            ["stat", "--decomposition-depths"], registry=registry
        )
    assert exit_code == 0
    payload = json.loads(buffer.getvalue())
    assert payload == {
        "decomposition_depths": {
            "0": 2,
            "1": 1,
            "2": 1,
        }
    }


def test_stat_without_job_id_mentions_decomposition_depths_flag(tmp_path: Path) -> None:
    from contextlib import redirect_stderr

    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    buffer = io.StringIO()
    with redirect_stderr(buffer):
        exit_code = coordinator_cli.main(["stat"], registry=registry)
    assert exit_code == 1
    assert "--decomposition-depths" in buffer.getvalue()
