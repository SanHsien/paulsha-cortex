"""Tests for issue #273: monitor refresh silent failures, duplicate checkouts, and source collisions."""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from paulsha_cortex.monitor.config import MonitorConfig
from paulsha_cortex.monitor.correlation import correlate_work_sources
from paulsha_cortex.monitor.models import ProjectState
from paulsha_cortex.monitor.service import ProjectMonitorService
from paulsha_cortex.monitor.work_api import (
    WorkModelRefresher,
    WorkReadModelStore,
)
from paulsha_cortex.monitor.work_models import WorkSource
from paulsha_cortex.monitor.work_snapshot import WorkSnapshot, WorkSnapshotStore
from paulsha_cortex.coordinator.claim import load_work_authority


def test_refresh_failure_observability_and_logging(tmp_path: Path, caplog: pytest.CapLogFixture) -> None:
    """Defect 1: refresh exceptions are logged and tracked in store status."""
    read_store = WorkReadModelStore.empty()
    assert getattr(read_store, "last_refresh_error", None) is None
    assert getattr(read_store, "consecutive_refresh_failures", 0) == 0

    mock_refresher = MagicMock(spec=WorkModelRefresher)
    mock_refresher.refresh.side_effect = ValueError("Frontmatter work_item mismatch in proposal.md")

    svc = ProjectMonitorService(
        config=MonitorConfig(workspaces=(), socket_path=tmp_path / "test.sock"),
        work_store=read_store,
        work_refresher=mock_refresher,
    )

    with caplog.at_level(logging.ERROR):
        svc._refresh_work_model(include_github=False)

    # 1. Logging verification: must write log when ValueError occurs
    assert any("Frontmatter work_item mismatch" in rec.message for rec in caplog.records)

    # 2. Status verification: consecutive failures and last error must be recorded
    assert read_store.consecutive_refresh_failures == 1
    assert "Frontmatter work_item mismatch" in str(read_store.last_refresh_error)

    # Second failure increments failure count
    with caplog.at_level(logging.ERROR):
        svc._refresh_work_model(include_github=False)

    assert read_store.consecutive_refresh_failures == 2

    # Success resets consecutive failure count
    mock_refresher.refresh.side_effect = None
    mock_refresher.refresh.return_value = ()
    svc._refresh_work_model(include_github=False)

    assert read_store.consecutive_refresh_failures == 0
    assert read_store.last_refresh_error is None


def test_work_show_and_start_error_messaging_on_refresh_failure() -> None:
    """Defect 1: get_work_item & load_work_authority report root cause when refresh failed."""
    read_store = WorkReadModelStore.empty()
    read_store.record_refresh_failure(ValueError("Frontmatter collision in repo X"))

    # get_work_item on missing item when refresh failed
    with pytest.raises(KeyError) as exc_info:
        read_store.get_work_item("nonexistent-item", repo="test/repo")
    assert "Frontmatter collision" in str(exc_info.value) or "refresh" in str(exc_info.value).lower()

    # load_work_authority on snapshot payload containing last_refresh_error
    snapshot_data = {
        "schema": "work-items-snapshot/v1",
        "sequence": 1,
        "written_at": "2026-07-31T00:00:00Z",
        "providers": {},
        "work_items": [],
        "source_owners": {},
        "exclusions": [],
        "last_refresh_error": "Frontmatter collision in repo X",
        "consecutive_refresh_failures": 3,
    }
    with patch("paulsha_cortex.coordinator.claim._load_snapshot") as mock_load:
        mock_load.return_value = (snapshot_data, "digest123")
        with pytest.raises(ValueError) as claim_exc:
            load_work_authority(repo="test/repo", work_id="nonexistent-item")
        assert "Frontmatter collision" in str(claim_exc.value) or "refresh" in str(claim_exc.value).lower()


def test_duplicate_checkout_same_repo_deduplication(tmp_path: Path) -> None:
    """Defect 2: multiple checkouts of same repo don't throw opaque duplicate work item ID."""
    repo_dir = tmp_path / "my-repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()  # canonical git repo dir

    wt_dir = tmp_path / "my-repo-wt"
    wt_dir.mkdir()
    (wt_dir / ".git").write_text("gitdir: /path/to/git\n")  # sibling worktree file

    work_yaml = """
version: 1
work_items:
  item-1:
    title: "Item 1"
    links:
      - kind: path
        ref: "docs/superpowers/workstreams/ws1/todo.md"
"""
    (repo_dir / ".cortex").mkdir()
    (repo_dir / ".cortex" / "work-items.yaml").write_text(work_yaml)
    todo_dir1 = repo_dir / "docs" / "superpowers" / "workstreams" / "ws1"
    todo_dir1.mkdir(parents=True)
    (todo_dir1 / "todo.md").write_text("# TODO\n<!-- work_item: item-1 -->\n- [ ] task\n")

    (wt_dir / ".cortex").mkdir()
    (wt_dir / ".cortex" / "work-items.yaml").write_text(work_yaml)
    todo_dir2 = wt_dir / "docs" / "superpowers" / "workstreams" / "ws1"
    todo_dir2.mkdir(parents=True)
    (todo_dir2 / "todo.md").write_text("# TODO\n<!-- work_item: item-1 -->\n- [ ] task\n")

    projects = (
        ProjectState(project_id="my-org/my-repo", workspace="my-repo", path=str(repo_dir)),
        ProjectState(project_id="my-org/my-repo", workspace="my-repo-wt", path=str(wt_dir)),
    )

    durable_store = WorkSnapshotStore(path=tmp_path / "snapshot.json")
    read_store = WorkReadModelStore.empty()
    refresher = WorkModelRefresher(durable_store=durable_store, read_store=read_store)

    # Must NOT raise ValueError("duplicate work item ID")
    refresher.refresh(projects, include_github=False)

    snapshot = read_store.current_snapshot()
    # Check that canonical project work item exists
    work_ids = [item.work_id for item in snapshot.work_items]
    assert "item-1" in work_ids

    # Check provider diagnostics include directory paths of collision
    repo_provider = snapshot.providers.get("repo:my-org/my-repo")
    assert repo_provider is not None
    assert any("my-repo-wt" in diag or "duplicate checkout" in diag for diag in repo_provider.diagnostics)


def test_source_collision_localized_projection_impact(tmp_path: Path) -> None:
    """Defect 3: single source collision degrades repo but does not wipe all unrelated work items."""
    # Setup sources where item-1 and item-2 collide on openspec change-1, but item-3 is healthy on todo:tasks.md
    change_dir = tmp_path / "openspec" / "changes" / "change-1"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("---\nwork_item: item-1\n---\n")
    (change_dir / "tasks.md").write_text("---\nwork_item: item-2\n---\n")

    tasks_file = tmp_path / "tasks.md"
    tasks_file.write_text("---\nwork_item: item-3\n---\n# TODO\n- [ ] do task 3\n")

    source_colliding_1 = WorkSource(
        source_id="openspec:change-1",
        kind="openspec",
        ref="change-1",
        status="active",
        revision="rev1",
        confidence="confirmed",
        provider="repo:my-org/my-repo",
    )
    source_healthy = WorkSource(
        source_id="todo:tasks.md",
        kind="todo",
        ref="tasks.md",
        status="active",
        revision="rev2",
        confidence="confirmed",
        provider="repo:my-org/my-repo",
    )

    sources = (source_colliding_1, source_healthy)
    res = correlate_work_sources(
        repo_root=tmp_path,
        repo="my-org/my-repo",
        sources=sources,
    )

    # 1. Correlation must be marked degraded
    assert res.degraded is True
    assert any("confirmed source collision: openspec:change-1" in diag for diag in res.diagnostics)

    # 2. Healthy work item (item-3) MUST still be projected in groups!
    group_work_ids = {group.work_id for group in res.groups}
    assert "item-3" in group_work_ids
