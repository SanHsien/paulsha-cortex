"""Durable, cross-restart backoff bookkeeping for GitHub provider rate limits.

#370: `resume_workflow_run` hitting a rate-limited GitHub provider must not
retry immediately -- an in-process-only cooldown would reset on every daemon
restart and race straight back into the same 403/secondary-rate-limit wall.
This module persists the next-retry deadline to a small JSON file under the
coordinator state root so it survives restarts, and grows the deadline with
the same exponential curve already used for periodic-tick backoff
(``backoff.tick_backoff_seconds``, extracted from ``manager_daemon.py``'s
issue #249 mechanism specifically so this module could reuse it without a
circular import).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .backoff import tick_backoff_seconds

STATE_FILENAME = "provider-rate-limit-backoff.json"
SCHEMA = "provider-rate-limit-backoff/v1"
# 5 minutes: shorter than GitHub's primary rate-limit window (resets hourly)
# but long enough that a burst of resume attempts doesn't hammer a provider
# that's still within its secondary/abuse-detection cooldown. Consecutive
# hits grow this exponentially (see `tick_backoff_seconds`), capped at 16x
# (~80 minutes) -- comfortably past a primary-window reset.
BASE_BACKOFF_SECONDS = 300.0


@dataclass(frozen=True)
class RateLimitBackoff:
    deadline_epoch: float
    consecutive_hits: int


def _state_path(coordinator_root: str | Path) -> Path:
    return Path(coordinator_root) / STATE_FILENAME


def _read_providers(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        return {}
    providers = payload.get("providers")
    return providers if isinstance(providers, dict) else {}


def _write_providers(path: Path, providers: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": SCHEMA, "providers": providers}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def active_backoff(
    coordinator_root: str | Path, provider_id: str, *, now: float
) -> RateLimitBackoff | None:
    """Return the still-active backoff for *provider_id*, or ``None`` if expired/absent.

    Always re-reads from disk -- no in-process cache -- so this reflects
    the durable state even immediately after a (simulated) daemon restart.
    """
    providers = _read_providers(_state_path(coordinator_root))
    entry = providers.get(provider_id)
    if not isinstance(entry, dict):
        return None
    deadline = entry.get("deadline_epoch")
    hits = entry.get("consecutive_hits")
    if not isinstance(deadline, (int, float)) or isinstance(deadline, bool):
        return None
    if not isinstance(hits, int) or isinstance(hits, bool) or hits < 1:
        hits = 1
    if float(deadline) <= now:
        return None
    return RateLimitBackoff(deadline_epoch=float(deadline), consecutive_hits=hits)


def record_backoff(
    coordinator_root: str | Path, provider_id: str, *, now: float
) -> RateLimitBackoff:
    """Persist a fresh (or extended) rate-limit backoff deadline for *provider_id*.

    Consecutive hits are tracked durably and grow the deadline along the
    same exponential curve as periodic-tick backoff, so a persistently
    rate-limited provider backs off further each time instead of being
    re-hit on the same cadence forever.
    """
    path = _state_path(coordinator_root)
    providers = _read_providers(path)
    existing = providers.get(provider_id)
    previous_hits = (
        existing.get("consecutive_hits")
        if isinstance(existing, dict) and isinstance(existing.get("consecutive_hits"), int)
        else 0
    )
    hits = previous_hits + 1
    deadline = now + tick_backoff_seconds(BASE_BACKOFF_SECONDS, hits)
    providers[provider_id] = {"deadline_epoch": deadline, "consecutive_hits": hits}
    _write_providers(path, providers)
    return RateLimitBackoff(deadline_epoch=deadline, consecutive_hits=hits)


def clear_backoff(coordinator_root: str | Path, provider_id: str) -> None:
    """Drop a provider's backoff record, e.g. once it's observed healthy again."""
    path = _state_path(coordinator_root)
    providers = _read_providers(path)
    if provider_id in providers:
        del providers[provider_id]
        _write_providers(path, providers)
