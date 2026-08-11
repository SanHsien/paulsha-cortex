"""#384：slice lane（`complete_tick`）的 typed provider failure 分類與
`cortex inspect status` 投影接線測試。

Root cause：`manager.py` 的 slice lane 過去在 build-phase failure 時一律把
``gate_reason`` 寫死成 ``"builder-failed"``，無分類；`slice_status_entry`／
handoff manifest 也沒有欄位可以承載分類結果，`cortex inspect status` 因此永遠
看不出是哪一種 executor 失敗。本檔驗證：

- `complete_tick` 對已分類（`job["provider_outcome"]` 非 None）的 build-phase
  failure，把 outcome 併進 `gate_reason`，並把完整分類寫進 handoff manifest 的
  `provider_outcome` 欄位。
- 未分類（legacy／繞過 dispatcher 的 job）維持既有 `"builder-failed"` 字面值，
  不偽造分類——保護所有既有呼叫端。
- `slice_status_entry` 把 manifest 上的 `provider_outcome` 投影進回傳的狀態
  entry，供 `cortex inspect status` 的 `attention` 清單顯示。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from paulsha_cortex.coordinator import manager
from paulsha_cortex.coordinator.registry import JobRegistry


class _FakeDispatcher:
    """複用 test_coordinator_manager.py 的樣板：包真 JobRegistry，poll 依腳本轉態。"""

    def __init__(self, registry: JobRegistry, poll_map: dict | None = None) -> None:
        self._registry = registry
        self._poll_map = poll_map or {}

    def poll_headless_done(self, job_id: str) -> dict:
        status = self._poll_map.get(job_id)
        if status is None:
            return self._registry.get_job(job_id)
        return self._registry.update_headless_result(job_id, status=status, exit_code=1)


def _reg(tmp: str) -> JobRegistry:
    return JobRegistry(state_path=Path(tmp) / "jobs.json")


def _make_job(reg: JobRegistry, slice_id: str) -> dict:
    return reg.create_job(
        task=slice_id,
        persona="builder",
        branch=f"feature/{slice_id}",
        pane="",
        worktree=f"/wt/{slice_id}",
        executor="copilot",
        session_name=slice_id,
        pid=4242,
        log_path=f"/logs/{slice_id}.jsonl",
    )


def test_complete_tick_enriches_gate_reason_with_classified_provider_outcome() -> None:
    with tempfile.TemporaryDirectory() as d:
        reg = _reg(d)
        job = _make_job(reg, "slice-rl")
        # 已由 dispatcher 分類過的 job（模擬 Dispatcher._finalize_headless 的
        # 產出）——complete_tick 不重新分類，只讀回既有分類。
        reg.update_headless_result(
            job["job_id"],
            status="failed",
            exit_code=1,
            provider_outcome={
                "outcome": "rate_limited",
                "authority": "text_signal",
                "reason": "rate limit signal detected in executor output",
                "retryable": True,
            },
        )
        disp = _FakeDispatcher(reg, poll_map={})
        hdir = Path(d) / "handoff"

        manager.complete_tick(disp, handoff_dir=str(hdir), clock=lambda: "T0")

        manifest = json.loads((hdir / "slice-rl.json").read_text(encoding="utf-8"))
        assert manifest["gate_status"] == "failed"
        assert manifest["gate_reason"] == "builder-failed-rate_limited"
        assert manifest["provider_outcome"] == {
            "outcome": "rate_limited",
            "authority": "text_signal",
            "reason": "rate limit signal detected in executor output",
            "retryable": True,
        }


def test_complete_tick_keeps_legacy_reason_when_job_has_no_classification() -> None:
    with tempfile.TemporaryDirectory() as d:
        reg = _reg(d)
        job = _make_job(reg, "slice-legacy")
        disp = _FakeDispatcher(reg, poll_map={job["job_id"]: "failed"})
        hdir = Path(d) / "handoff"

        manager.complete_tick(disp, handoff_dir=str(hdir), clock=lambda: "T0")

        manifest = json.loads((hdir / "slice-legacy.json").read_text(encoding="utf-8"))
        assert manifest["gate_reason"] == "builder-failed"
        assert manifest["provider_outcome"] is None


def test_slice_status_entry_projects_provider_outcome_from_manifest() -> None:
    with tempfile.TemporaryDirectory() as d:
        reg = _reg(d)
        job = _make_job(reg, "slice-content")
        reg.update_headless_result(
            job["job_id"],
            status="failed",
            exit_code=1,
            provider_outcome={
                "outcome": "content",
                "authority": "text_signal",
                "reason": "content-policy signal detected in executor output",
                "retryable": False,
            },
        )
        disp = _FakeDispatcher(reg, poll_map={})
        hdir = Path(d) / "handoff"
        manager.complete_tick(disp, handoff_dir=str(hdir), clock=lambda: "T0")

        slice_row = {
            "slice_id": "slice-content",
            "builder_job_id": job["job_id"],
            "reviewer_job_id": None,
            "actions": [],
            "state": "needs_human",
            "gate_state": "needs_human",
            "current_evidence_refs": [],
            "current_evaluation_refs": [],
        }
        entry = manager.slice_status_entry(reg, slice_row, handoff_dir=str(hdir))
        assert entry["provider_outcome"] == {
            "outcome": "content",
            "authority": "text_signal",
            "reason": "content-policy signal detected in executor output",
            "retryable": False,
        }
        assert entry["reason"] == "builder-failed-content"


def test_slice_status_entry_provider_outcome_is_none_without_manifest_classification() -> None:
    with tempfile.TemporaryDirectory() as d:
        reg = _reg(d)
        job = _make_job(reg, "slice-noclassify")
        disp = _FakeDispatcher(reg, poll_map={job["job_id"]: "failed"})
        hdir = Path(d) / "handoff"
        manager.complete_tick(disp, handoff_dir=str(hdir), clock=lambda: "T0")

        slice_row = {
            "slice_id": "slice-noclassify",
            "builder_job_id": job["job_id"],
            "reviewer_job_id": None,
            "actions": [],
            "state": "needs_human",
            "gate_state": "needs_human",
            "current_evidence_refs": [],
            "current_evaluation_refs": [],
        }
        entry = manager.slice_status_entry(reg, slice_row, handoff_dir=str(hdir))
        assert entry["provider_outcome"] is None
