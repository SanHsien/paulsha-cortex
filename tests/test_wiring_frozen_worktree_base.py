"""#208 收口 wiring 5（#211 閉環）：dispatch 建 builder worktree 消費凍結 base SHA。

落點：``manager._dispatch_workflow_card`` 建 builder worktree 的
``ScriptWorktreeCreator.create()`` 呼叫（grep ``worktree`` 定位）。

驗收條件對應：
1. run 帶 ``frozen_readiness``（#211 掛在 run 上的凍結集）時，worktree 以
   ``frozen_readiness["base_sha"]`` 為基底建立（「確實發生」：creator 收到的
   ``base_sha`` 引數等於凍結值，而非現行 HEAD）。
2. 無凍結集時完全不傳 ``base_sha`` 引數，維持現行為——連舊版
   ``WorktreeCreator`` 實作（不接受 ``base_sha`` 關鍵字引數）都不受影響。
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from paulsha_cortex.coordinator import manager
from paulsha_cortex.coordinator.launcher import LaunchHandle
from paulsha_cortex.coordinator.model_identities import IdentityRegistry
from paulsha_cortex.coordinator.registry import JobRegistry
from paulsha_cortex.coordinator.workflow import WorkflowStep

_REPO = "hamanpaul/paulsha-cortex"


class _CommitLauncher:
    def launch(self, *, slice_id: str, prompt: str, worktree: str, log_dir: str) -> LaunchHandle:
        return LaunchHandle(
            executor="copilot", model_id="gpt", session_name=slice_id, pid=100,
            log_path=f"{log_dir}/{slice_id}.jsonl",
        )

    def as_commit_required(self):
        return self


class _RecordingCreator:
    """比照 test_multi_issue_worktree.py 的 fake，額外記錄 base_sha 引數。

    ``calls`` 記錄每次呼叫收到的 ``(branch, base_sha)`` 二元組——用
    ``**kwargs.get("base_sha")`` 而非固定形參簽章，才能同時偵測「完全沒傳這個
    關鍵字引數」（驗收條件 2）與「傳了且值正確」（驗收條件 1）兩種情況。
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.calls: list[tuple[str, object]] = []

    def create(self, branch: str, **kwargs: object) -> str:
        self.calls.append((branch, kwargs.get("base_sha", "<not-passed>")))
        return str(self.repo_root)


def _init_repo(root: Path) -> str:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(root), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test User"], check=True)
    (root / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
    ).stdout.strip()


def _build_run(registry: JobRegistry, workspace_root: Path, *, frozen_readiness=None):
    step = WorkflowStep(
        phase="build",
        persona="builder",
        card="tdd-red",
        executor="copilot",
        model="gpt",
        domain="openai",
        inputs=(),
        outputs=(),
        commit_policy="required",
        test_policy="red-required",
        gate_result="pending",
    )
    return registry._manager_create_workflow_run(
        work_id="frozen-worktree-base-208",
        repo=_REPO,
        claim_key="claim:v1:" + "1" * 64,
        source_revision="2" * 64,
        workspace_root=str(workspace_root),
        combo="feature-oneshot",
        current_phase="build",
        steps=(step,),
        issue_refs=(f"{_REPO}#211",),
        openspec_refs=("frozen-worktree-base-208",),
        pr_refs=(),
        attempts={"build": 1},
        gate_status="running",
        frozen_readiness=frozen_readiness,
    )


def _dispatch(run, registry: JobRegistry, creator: _RecordingCreator, tmp_path: Path):
    dispatcher = type(
        "D", (), {"_registry": registry, "_worktree_creator": creator, "_git_runner": None},
    )()
    job = manager.dispatch_workflow_card(
        dispatcher,
        run=run,
        identities=IdentityRegistry.from_rows(
            [{
                "executor": "copilot",
                "model_id": "gpt",
                "independence_domain": "openai",
                "capabilities": ["build"],
            }]
        ),
        launcher_factory=lambda _: _CommitLauncher(),
        coordinator_root=tmp_path / "coordinator",
    )
    assert job is not None
    return job


def _frozen_readiness(*, base_sha: str) -> dict[str, Any]:
    return {
        "schema": "pre-claim-readiness-frozen-set/v1",
        "repo": _REPO,
        "work_id": "frozen-worktree-base-208",
        "base_sha": base_sha,
        "planning_authority_hashes": ["a" * 64],
        "monitor_snapshot_revision": "snap-1",
        "issue_ref": f"{_REPO}#211",
        "executor_identity": "copilot:gpt",
        "frozen_at_epoch": 1_000.0,
        "live_probe_ttl_cached": False,
    }


def test_frozen_readiness_present_builds_worktree_from_its_base_sha(tmp_path: Path) -> None:
    workspace = tmp_path / "run-repo"
    initial_head = _init_repo(workspace)
    # 之後 HEAD 前進一個新 commit——凍結集裡的 base_sha 必須是「先前凍結」的
    # initial_head，不是目前的新 HEAD（否則就是 hippo #18 #2／#41 v2 的
    # stale-base 缺陷本身）。
    (workspace / "later.txt").write_text("later\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(workspace), "add", "later.txt"], check=True)
    subprocess.run(["git", "-C", str(workspace), "commit", "-qm", "later"], check=True)

    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    run = _build_run(
        registry, workspace_root=workspace, frozen_readiness=_frozen_readiness(base_sha=initial_head)
    )
    creator = _RecordingCreator(workspace)

    job = _dispatch(run, registry, creator, tmp_path)

    assert creator.calls == [("feature/211-frozen-worktree-base-208", initial_head)]
    assert job["branch"] == "feature/211-frozen-worktree-base-208"


def test_no_frozen_readiness_omits_base_sha_argument_entirely(tmp_path: Path) -> None:
    workspace = tmp_path / "run-repo"
    _init_repo(workspace)
    registry = JobRegistry(state_path=tmp_path / "jobs.json")
    run = _build_run(registry, workspace_root=workspace, frozen_readiness=None)
    creator = _RecordingCreator(workspace)

    job = _dispatch(run, registry, creator, tmp_path)

    # "<not-passed>" 是 sentinel：證明 base_sha 這個關鍵字引數根本沒被傳入，
    # 不是傳了 None——維持現行為給不接受 base_sha 的舊 WorktreeCreator 用。
    assert creator.calls == [("feature/211-frozen-worktree-base-208", "<not-passed>")]
    assert job["branch"] == "feature/211-frozen-worktree-base-208"
