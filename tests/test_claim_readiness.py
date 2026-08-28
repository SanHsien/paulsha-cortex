"""Focused tests for the #211 pre-claim readiness transaction (issue #208 A.2)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from paulsha_cortex.coordinator import claim_readiness as cr
from paulsha_cortex.coordinator.claim import WorkAuthority, load_work_authority


def _authority(tmp_path: Path, *, name: str = "snapshot.json") -> WorkAuthority:
    payload = {
        "schema": "work-items-snapshot/v1",
        "providers": {
            "github": {
                "provider_id": "github",
                "revision": "github-rev-1",
                "last_success_epoch": 950,
                "degraded": False,
            }
        },
        "work_items": [
            {
                "repo": "acme/demo",
                "work_id": "readiness",
                "mapped_issues": [211],
                "mapped_prs": [],
                "mapped_openspec": ["readiness"],
                "mapped_todo_paths": ["docs/todo.md"],
                "confirmed_todo": True,
                "auto_label": True,
                "source_revisions": ["issue:211@open", "openspec:readiness@abc"],
            }
        ],
    }
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return load_work_authority(repo="acme/demo", work_id="readiness", snapshot_path=path)


def _passing_probes(**overrides) -> cr.ReadinessProbes:
    base = dict(
        local_scope=cr.local_scope_probe(),
        base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_fixed_git_runner("a" * 40)),
        monitor_snapshot=cr.monitor_snapshot_probe(),
        github_owner=cr.github_owner_probe(
            runner=lambda *a, **k: SimpleNamespace(
                returncode=0, stdout=json.dumps({"state": "open"}), stderr=""
            )
        ),
        capability=cr.capability_probe(),
        live_probe=cr.live_probe_check(prober=lambda: SimpleNamespace(ready=True)),
    )
    base.update(overrides)
    return cr.ReadinessProbes(**base)


def _fixed_git_runner(remote_sha: str):
    def _run(args: list[str]):
        if "fetch" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if "rev-parse" in args:
            return SimpleNamespace(returncode=0, stdout=f"{remote_sha}\n", stderr="")
        raise AssertionError(f"unexpected git invocation: {args}")

    return _run


# ---------------------------------------------------------------------------
# AC1: cost-ordered execution, live probe last + TTL cached
# ---------------------------------------------------------------------------


def test_checks_run_in_declared_cost_order_and_live_probe_is_last(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    probes = _passing_probes(
        base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_fixed_git_runner("a" * 40)),
    )
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1000.0)
    assert outcome.checks_run == cr.CHECK_ORDER
    assert outcome.checks_run[-1] == "live_probe"
    assert outcome.ready is True


def test_short_circuits_before_paying_for_more_expensive_checks(tmp_path: Path) -> None:
    """A cheap check failing must never invoke the expensive checks after it."""

    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    called = []

    def _spy(name):
        def _probe(_context):
            called.append(name)
            return cr._passed(name)

        return _probe

    probes = cr.ReadinessProbes(
        local_scope=lambda _ctx: cr._failed("local_scope", "heading-gap"),
        base_sha=_spy("base_sha"),
        monitor_snapshot=_spy("monitor_snapshot"),
        github_owner=_spy("github_owner"),
        capability=_spy("capability"),
        live_probe=_spy("live_probe"),
    )
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1000.0)
    assert outcome.ready is False
    assert outcome.failed_check == "local_scope"
    assert called == []
    assert outcome.checks_run == ("local_scope",)


def test_live_probe_ttl_cache_avoids_repeated_real_probes(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    probe_calls = []

    def _prober():
        probe_calls.append(1)
        return SimpleNamespace(ready=True)

    probes = _passing_probes(
        base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_fixed_git_runner("a" * 40)),
        live_probe=cr.live_probe_check(prober=_prober),
    )
    cache = cr.LiveProbeCache(ttl_seconds=100.0)
    first = cr.evaluate_pre_claim_readiness(context, probes, live_probe_cache=cache, now=lambda: 1000.0)
    second = cr.evaluate_pre_claim_readiness(context, probes, live_probe_cache=cache, now=lambda: 1010.0)
    assert first.ready and second.ready
    assert len(probe_calls) == 1
    assert first.frozen.live_probe_ttl_cached is False
    assert second.frozen.live_probe_ttl_cached is True


def test_live_probe_ttl_cache_expires_and_reprobes(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    probe_calls = []

    def _prober():
        probe_calls.append(1)
        return SimpleNamespace(ready=True)

    probes = _passing_probes(
        base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_fixed_git_runner("a" * 40)),
        live_probe=cr.live_probe_check(prober=_prober),
    )
    cache = cr.LiveProbeCache(ttl_seconds=5.0)
    cr.evaluate_pre_claim_readiness(context, probes, live_probe_cache=cache, now=lambda: 1000.0)
    cr.evaluate_pre_claim_readiness(context, probes, live_probe_cache=cache, now=lambda: 1010.0)
    assert len(probe_calls) == 2


# ---------------------------------------------------------------------------
# AC2: output is a frozen set carrying SHA/hash values, not a boolean
# ---------------------------------------------------------------------------


def test_success_returns_frozen_set_not_a_boolean(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    context = cr.ReadinessContext(
        authority=authority, executor_identity="agy:gemini", issue_ref="acme/demo#211"
    )
    remote_sha = "c" * 40
    probes = _passing_probes(base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_fixed_git_runner(remote_sha)))
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1234.5)
    assert isinstance(outcome, cr.ReadinessOutcome)
    assert isinstance(outcome.frozen, cr.FrozenReadinessSet)
    assert outcome.frozen.base_sha == remote_sha
    assert outcome.frozen.planning_authority_hashes
    assert outcome.frozen.monitor_snapshot_revision == authority.snapshot_hash
    assert outcome.frozen.issue_ref == "acme/demo#211"
    assert outcome.frozen.frozen_at_epoch == 1234.5


def test_frozen_set_round_trips_through_dict(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    probes = _passing_probes(base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_fixed_git_runner("d" * 40)))
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 42.0)
    payload = outcome.frozen.to_dict()
    restored = cr.FrozenReadinessSet.from_dict(payload)
    assert restored == outcome.frozen


def test_frozen_set_rejects_malformed_payload() -> None:
    with pytest.raises(ValueError, match="schema invalid"):
        cr.FrozenReadinessSet.from_dict({"schema": "wrong"})


# ---------------------------------------------------------------------------
# AC3: builder worktree must use the frozen base SHA — stale base is caught,
# and a later drift in "current remote main" cannot silently reappear once frozen.
# ---------------------------------------------------------------------------


def test_stale_local_base_is_rejected_before_freeze(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    probes = _passing_probes(
        base_sha=cr.base_sha_probe(
            repo_root="/unused",
            git_runner=_fixed_git_runner("e" * 40),
            local_known_base_sha="f" * 40,
        ),
    )
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1000.0)
    assert outcome.ready is False
    assert outcome.failed_check == "base_sha"
    assert outcome.reason == "stale-base"
    assert outcome.frozen is None
    assert outcome.terminal is False


def test_frozen_base_sha_is_immutable_once_captured(tmp_path: Path) -> None:
    """Once frozen, a later drift in what remote main *now* points to must not
    silently change the already-returned frozen value: it is a value object,
    not a live pointer back at the repo."""

    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    first_sha = "1" * 40
    probes = _passing_probes(base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_fixed_git_runner(first_sha)))
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1000.0)
    frozen = outcome.frozen
    assert frozen.base_sha == first_sha

    # Remote main has since moved; the frozen value from the earlier
    # transaction must be unaffected (dataclass is frozen too).
    with pytest.raises(Exception):
        frozen.base_sha = "2" * 40  # type: ignore[misc]
    assert frozen.base_sha == first_sha


# ---------------------------------------------------------------------------
# AC4: terminal vs. retryable classification; policy-scope conflict is terminal
# ---------------------------------------------------------------------------


def test_heading_gap_is_retryable_not_terminal(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    probes = _passing_probes(local_scope=cr.local_scope_probe(heading_ok=False))
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1000.0)
    assert outcome.ready is False
    assert outcome.reason == "heading-gap"
    assert outcome.terminal is False


def test_policy_scope_conflict_is_terminal_and_never_retried(tmp_path: Path) -> None:
    """hippo #18 point 9: R-09 requires a changelog fragment while the frozen
    scope explicitly forbids one — an unsatisfiable contract that must resolve
    straight to needs_human, never loop back into a retry."""

    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    probes = _passing_probes(
        local_scope=cr.local_scope_probe(changelog_required=True, changelog_forbidden=True),
    )
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1000.0)
    assert outcome.ready is False
    assert outcome.failed_check == "local_scope"
    assert outcome.reason == "policy-scope-conflict"
    assert outcome.terminal is True


def test_owner_transfer_incomplete_is_retryable(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    probes = _passing_probes(
        base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_fixed_git_runner("a" * 40)),
        monitor_snapshot=cr.monitor_snapshot_probe(owner_count=2),
    )
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1000.0)
    assert outcome.ready is False
    assert outcome.reason == "owner-transfer-incomplete"
    assert outcome.terminal is False


def test_capability_unavailable_is_an_observable_bypass_not_a_failure(tmp_path: Path) -> None:
    """#209's capability table has not landed; absent lookup must pass through
    (with an observability marker), not fail closed."""

    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    probes = _passing_probes(
        base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_fixed_git_runner("a" * 40)),
        capability=cr.capability_probe(capability_lookup=None),
    )
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1000.0)
    assert outcome.ready is True


def test_capability_insufficient_fails_closed(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    probes = _passing_probes(
        base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_fixed_git_runner("a" * 40)),
        capability=cr.capability_probe(capability_lookup=lambda _identity: False),
    )
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1000.0)
    assert outcome.ready is False
    assert outcome.reason == "capability-insufficient"
    assert outcome.terminal is False


def test_live_probe_failure_is_retryable(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    context = cr.ReadinessContext(authority=authority, executor_identity="agy:gemini")
    probes = _passing_probes(
        base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_fixed_git_runner("a" * 40)),
        live_probe=cr.live_probe_check(prober=lambda: SimpleNamespace(ready=False, reason="models-probe-failed")),
    )
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1000.0)
    assert outcome.ready is False
    assert outcome.failed_check == "live_probe"
    assert outcome.reason == "models-probe-failed"
    assert outcome.terminal is False


def test_github_owner_link_mismatch_blocks_before_capability_and_live_probe(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    context = cr.ReadinessContext(
        authority=authority, executor_identity="agy:gemini", issue_ref="acme/demo#211"
    )
    probes = _passing_probes(
        base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_fixed_git_runner("a" * 40)),
        github_owner=cr.github_owner_probe(
            runner=lambda *a, **k: SimpleNamespace(returncode=0, stdout=json.dumps({"state": "closed"}), stderr="")
        ),
    )
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1000.0)
    assert outcome.ready is False
    assert outcome.failed_check == "github_owner"
    assert outcome.reason == "github-owner-link-mismatch"


# ---------------------------------------------------------------------------
# ReadinessCheckResult invariants
# ---------------------------------------------------------------------------


def test_check_result_rejects_passed_with_reason() -> None:
    with pytest.raises(ValueError, match="must not carry reason"):
        cr.ReadinessCheckResult(name="local_scope", passed=True, reason="oops")


def test_check_result_rejects_failed_without_reason() -> None:
    with pytest.raises(ValueError, match="requires a reason"):
        cr.ReadinessCheckResult(name="local_scope", passed=False)
