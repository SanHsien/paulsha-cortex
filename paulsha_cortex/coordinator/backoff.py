"""Pure exponential backoff curve shared across retry/backoff consumers.

Originally private to ``manager_daemon.py`` (periodic-tick failure
resilience, issue #249). Extracted so the durable GitHub provider
rate-limit backoff (``provider_backoff.py``, #370) can reuse the exact same
curve without ``provider_backoff`` importing ``manager_daemon`` (which would
be circular: ``manager_daemon`` already imports ``manager``, and
``manager``'s ``resume_workflow_run`` needs ``provider_backoff``).
``manager_daemon`` re-exports :func:`tick_backoff_seconds` as
``_tick_backoff_seconds`` for source compatibility.
"""

from __future__ import annotations

BACKOFF_MULTIPLIER_BASE = 2.0
BACKOFF_MAX_EXPONENT = 4  # caps backoff at base_interval * 2**4 = 16x


def tick_backoff_seconds(base_interval: float, consecutive_failures: int) -> float:
    """Exponential backoff interval for the next retry.

    Doubles per consecutive failure, capped at ``BACKOFF_MAX_EXPONENT``
    doublings, so a persistently failing operation backs off instead of
    retrying at the base cadence forever. ``consecutive_failures <= 0`` (no
    prior failure) returns the unmodified ``base_interval``.
    """
    if consecutive_failures <= 0:
        return base_interval
    exponent = min(consecutive_failures, BACKOFF_MAX_EXPONENT)
    return base_interval * (BACKOFF_MULTIPLIER_BASE**exponent)
