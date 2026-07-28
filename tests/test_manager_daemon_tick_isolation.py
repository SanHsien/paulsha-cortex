"""#216 迴歸測試：periodic tick 的 execute() 不得被 auto-claim 單點失敗癱瘓。

背景：``build_periodic_tick_runner`` 的 ``execute()`` 呼叫
``manager.run_auto_claim_scan(...)``（或注入的 ``auto_claim_fn``）以前完全
沒有 try/except；一旦它 raise，整個 tick 立刻結束——後面的 workflow resume
迴圈與 ``run_tick`` 全部不會執行。本檔驗證 auto-claim 失敗後兩者仍會被
呼叫，且回傳的 summary 帶有可觀測的降級標記。
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from paulsha_cortex.coordinator import manager_daemon


def _resume_target_workflow() -> SimpleNamespace:
    return SimpleNamespace(
        run_id="run-1",
        work_id="demo",
        repo="acme/demo",
        status="ongoing",
        facets=(),
        current_phase="build",
        # 非 "claim:v1:" 前綴，短路掉 build_production_ship_validator 分支，
        # 讓這個測試專心驗證隔離行為，不用另外準備 ship validator 依賴。
        claim_key="claim:legacy:demo",
        source_revision="",
    )


def _dispatcher_with_resumable_workflow(tmp_path: Path) -> SimpleNamespace:
    workflow = _resume_target_workflow()
    registry = SimpleNamespace(
        _state_path=str(tmp_path / "jobs.json"),
        list_workflow_runs=lambda: [workflow],
    )
    return SimpleNamespace(_registry=registry, _git_runner=lambda args: "")


def test_periodic_tick_survives_auto_claim_failure_and_still_resumes_and_ticks(
    monkeypatch, tmp_path: Path
) -> None:
    dispatcher = _dispatcher_with_resumable_workflow(tmp_path)

    resume_calls: list[str] = []

    def fake_resume_workflow_run(
        dispatcher_arg,
        *,
        run_id,
        identities,
        launcher_factory,
        coordinator_root,
        ship_validator,
    ):
        resume_calls.append(run_id)

    monkeypatch.setattr(manager_daemon.manager, "resume_workflow_run", fake_resume_workflow_run)

    tick_calls: list[dict] = []

    def fake_run_tick(dispatcher_arg, **kwargs):
        tick_calls.append(kwargs)
        return {
            "dispatch_skipped": False,
            "dispatched": [],
            "completed": [],
            "errors": [],
            "reaped": None,
        }

    def failing_auto_claim() -> list[dict]:
        raise ValueError(
            "trusted repo registry did not resolve exactly one owner/name root"
        )

    runner = manager_daemon.build_periodic_tick_runner(
        dispatcher=dispatcher,
        specs_dir=str(tmp_path / "specs"),
        handoff_dir=str(tmp_path / "handoff"),
        launcher=object(),
        run_tick_fn=fake_run_tick,
        scan_specs_fn=lambda specs_dir: [],
        auto_claim_fn=failing_auto_claim,
        workflow_identity_registry=object(),
    )

    result = runner()

    # 單一子系統（auto-claim）失效不得癱瘓整輪：resume 迴圈與 run_tick
    # 仍然被呼叫。
    assert resume_calls == ["run-1"]
    assert len(tick_calls) == 1

    # auto_claims 退化為空 list，而不是讓例外往外傳。
    assert result["auto_claims"] == []
    # summary 明確反映這輪 auto-claim 降級了，不是靜默吞掉。
    assert result["auto_claim_failed"] is True
    assert "ValueError" in result["auto_claim_error"]
    assert "trusted repo registry" in result["auto_claim_error"]
    assert str(tmp_path) not in result["auto_claim_error"]


def test_periodic_tick_regression_no_failure_matches_existing_behavior(
    monkeypatch, tmp_path: Path
) -> None:
    """正常情況（auto-claim 不失敗）不得多出降級欄位，行為與現況完全相同。"""

    dispatcher = _dispatcher_with_resumable_workflow(tmp_path)

    resume_calls: list[str] = []

    def fake_resume_workflow_run(dispatcher_arg, **kwargs):
        resume_calls.append(kwargs["run_id"])

    monkeypatch.setattr(manager_daemon.manager, "resume_workflow_run", fake_resume_workflow_run)

    def fake_run_tick(dispatcher_arg, **kwargs):
        return {
            "dispatch_skipped": False,
            "dispatched": [],
            "completed": [],
            "errors": [],
            "reaped": None,
        }

    runner = manager_daemon.build_periodic_tick_runner(
        dispatcher=dispatcher,
        specs_dir=str(tmp_path / "specs"),
        handoff_dir=str(tmp_path / "handoff"),
        launcher=object(),
        run_tick_fn=fake_run_tick,
        scan_specs_fn=lambda specs_dir: [],
        auto_claim_fn=lambda: [{"work_id": "demo", "action": "claim"}],
        workflow_identity_registry=object(),
    )

    result = runner()

    assert resume_calls == ["run-1"]
    assert result["auto_claims"] == [{"work_id": "demo", "action": "claim"}]
    assert "auto_claim_failed" not in result
    assert "auto_claim_error" not in result
