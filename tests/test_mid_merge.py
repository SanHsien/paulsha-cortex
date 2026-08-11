"""`mid_merge.detect_merge_state()` 回歸測試（issue #395 唯一落地 code 骨架）。

全程在 tmp git repo fixture 內建構真實 merge conflict，不 mock git 本身；
比照 `tests/test_work_gc.py` 既有慣例。任一測試皆不得涉及真實
`~/.agents`／`paulsha-cortex-worktrees` 路徑。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from paulsha_cortex.coordinator.mid_merge import MergeState, detect_merge_state


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test User")
    (root / "f.txt").write_text("line1\n", encoding="utf-8")
    _git(root, "add", "f.txt")
    _git(root, "commit", "-qm", "init")


def _conflicting_merge(root: Path) -> str:
    """在 `root` 建立一個真實會衝突的 merge，回傳 MERGE_HEAD 應有的 sha（feature head）。"""
    _git(root, "checkout", "-qb", "feature")
    (root / "f.txt").write_text("feature change\n", encoding="utf-8")
    _git(root, "commit", "-qam", "feature")
    feature_head = _git(root, "rev-parse", "feature").stdout.strip()
    _git(root, "checkout", "-q", "main")
    (root / "f.txt").write_text("main change\n", encoding="utf-8")
    _git(root, "commit", "-qam", "main")
    subprocess.run(
        ["git", "-C", str(root), "merge", "-q", "feature"],
        capture_output=True,
        text=True,
        check=False,
    )  # 預期非零 exit（衝突），不用 check=True
    return feature_head


def test_no_merge_in_progress_returns_absent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)

    state = detect_merge_state(repo)

    assert state == MergeState(in_progress=False)


def test_conflicting_merge_detected_with_unmerged_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    feature_head = _conflicting_merge(repo)

    state = detect_merge_state(repo)

    assert state.in_progress is True
    assert state.merge_head == feature_head
    assert state.unmerged_paths == ("f.txt",)


def test_completed_merge_no_longer_in_progress(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _conflicting_merge(repo)

    (repo / "f.txt").write_text("resolved\n", encoding="utf-8")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-qm", "resolve merge")

    state = detect_merge_state(repo)

    assert state == MergeState(in_progress=False)


def test_conflicting_merge_detected_inside_git_worktree(tmp_path: Path) -> None:
    """核心情境（issue #395 型 1）：MERGE_HEAD 是 worktree 私有狀態，非共用 `.git`。"""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _git(repo, "checkout", "-qb", "lane")
    (repo / "f.txt").write_text("lane change\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "lane change")
    _git(repo, "checkout", "-q", "main")
    (repo / "f.txt").write_text("main change\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "main change")

    lane_worktree = tmp_path / "lane-worktree"
    _git(repo, "worktree", "add", str(lane_worktree), "lane")
    lane_head = _git(repo, "rev-parse", "main").stdout.strip()
    subprocess.run(
        ["git", "-C", str(lane_worktree), "merge", "-q", "main"],
        capture_output=True,
        text=True,
        check=False,
    )

    state = detect_merge_state(lane_worktree)

    assert state.in_progress is True
    assert state.merge_head == lane_head
    assert state.unmerged_paths == ("f.txt",)

    # 主 repo（另一個 worktree）完全不受影響——MERGE_HEAD 不是共用狀態。
    assert detect_merge_state(repo) == MergeState(in_progress=False)


def test_git_runner_failure_fails_open_to_absent(tmp_path: Path) -> None:
    def _raising_runner(args: list[str]) -> str:
        raise RuntimeError("not a git repo")

    state = detect_merge_state(tmp_path / "not-a-repo", git_runner=_raising_runner)

    assert state == MergeState(in_progress=False)


def test_injected_git_runner_used_instead_of_real_git(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def _fake_runner(args: list[str]) -> str:
        calls.append(args)
        if args[:2] == ["rev-parse", "--git-path"]:
            return ".git/MERGE_HEAD\n"
        if args[0] == "status":
            return "u UU N... 100644 100644 100644 100644 aaa bbb ccc conflicted.txt\n"
        raise AssertionError(f"unexpected git args: {args}")

    merge_head_dir = tmp_path / "repo" / ".git"
    merge_head_dir.mkdir(parents=True)
    (merge_head_dir / "MERGE_HEAD").write_text("deadbeef" * 5 + "\n", encoding="utf-8")

    state = detect_merge_state(tmp_path / "repo", git_runner=_fake_runner)

    assert state.in_progress is True
    assert state.merge_head == "deadbeef" * 5
    assert state.unmerged_paths == ("conflicted.txt",)
    assert calls[0][:2] == ["rev-parse", "--git-path"]
