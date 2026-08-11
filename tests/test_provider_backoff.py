"""#370: durable, cross-restart backoff bookkeeping for GitHub provider
rate limits. `resume_workflow_run` hitting a rate-limited GitHub provider
must not retry immediately -- an in-memory-only cooldown resets on daemon
restart and races straight back into the same 403, so the deadline has to
survive a restart (a fresh read from disk, not the same process)."""

from __future__ import annotations

from pathlib import Path

import pytest

from paulsha_cortex.coordinator import provider_backoff


def test_no_backoff_recorded_returns_none(tmp_path: Path) -> None:
    assert provider_backoff.active_backoff(tmp_path, "github:acme/demo", now=1000.0) is None


def test_record_backoff_is_immediately_active(tmp_path: Path) -> None:
    recorded = provider_backoff.record_backoff(tmp_path, "github:acme/demo", now=1000.0)
    assert recorded.deadline_epoch > 1000.0

    active = provider_backoff.active_backoff(tmp_path, "github:acme/demo", now=1000.0)
    assert active is not None
    assert active.deadline_epoch == recorded.deadline_epoch


def test_backoff_expires_after_its_deadline(tmp_path: Path) -> None:
    recorded = provider_backoff.record_backoff(tmp_path, "github:acme/demo", now=1000.0)
    assert provider_backoff.active_backoff(tmp_path, "github:acme/demo", now=recorded.deadline_epoch + 1) is None


def test_backoff_survives_a_fresh_process_read_from_disk(tmp_path: Path) -> None:
    """Durability contract: a brand new call (simulating a daemon restart --
    no shared in-memory state) must still see the deadline recorded by an
    earlier call, purely from what's on disk under coordinator_root."""
    provider_backoff.record_backoff(tmp_path, "github:acme/demo", now=1000.0)

    # Simulate "restart": a completely fresh read, same coordinator_root.
    active = provider_backoff.active_backoff(tmp_path, "github:acme/demo", now=1000.0)
    assert active is not None


def test_backoff_is_scoped_per_provider(tmp_path: Path) -> None:
    provider_backoff.record_backoff(tmp_path, "github:acme/demo", now=1000.0)
    assert provider_backoff.active_backoff(tmp_path, "github:acme/other", now=1000.0) is None


def test_consecutive_hits_extend_the_deadline_exponentially(tmp_path: Path) -> None:
    first = provider_backoff.record_backoff(tmp_path, "github:acme/demo", now=1000.0)
    # Second hit recorded right as the first deadline lands -- backs off further
    # than a single hit would, mirroring `backoff.tick_backoff_seconds`'s curve.
    second = provider_backoff.record_backoff(tmp_path, "github:acme/demo", now=first.deadline_epoch)
    assert second.consecutive_hits == first.consecutive_hits + 1
    assert (second.deadline_epoch - first.deadline_epoch) > (first.deadline_epoch - 1000.0)


def test_clear_backoff_removes_the_record(tmp_path: Path) -> None:
    provider_backoff.record_backoff(tmp_path, "github:acme/demo", now=1000.0)
    provider_backoff.clear_backoff(tmp_path, "github:acme/demo")
    assert provider_backoff.active_backoff(tmp_path, "github:acme/demo", now=1000.0) is None


def test_clear_backoff_on_absent_record_is_a_noop(tmp_path: Path) -> None:
    provider_backoff.clear_backoff(tmp_path, "github:acme/demo")  # must not raise


def test_corrupt_state_file_is_treated_as_no_backoff(tmp_path: Path) -> None:
    state_path = tmp_path / provider_backoff.STATE_FILENAME
    state_path.write_text("not json", encoding="utf-8")
    assert provider_backoff.active_backoff(tmp_path, "github:acme/demo", now=1000.0) is None
