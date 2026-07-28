"""Tick-failure resilience for the manager daemon's periodic scheduler.

Covers issue #249: a periodic tick that raises must not turn the
``tick_interval`` schedule into a hot loop. These tests exercise
``run_loop``'s failure-backoff, circuit-breaker, health-signal, and
error-log de-duplication behaviour using fully injected fake clocks/sleeps
(never a real ``time.sleep``).
"""

from __future__ import annotations

from paulsha_cortex.control import constants, contract
from paulsha_cortex.coordinator import manager_daemon


class _FakeClock:
    """Deterministic monotonic clock: value only advances via ``sleep``.

    Mirrors real ``time.monotonic()``/``time.sleep()`` semantics: multiple
    reads within the same "instant" (before any sleep) return the same
    value, and only the loop's end-of-round ``sleep_fn`` call moves time
    forward. This lets tests reason about elapsed wall-clock time across
    many rounds without ever performing a real sleep.
    """

    def __init__(self, start: float = 0.0) -> None:
        self.value = start

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


def _write_request(req_id: str, **overrides) -> dict:
    request = {
        "schema_version": constants.SCHEMA_VERSION,
        "req_id": req_id,
        "type": "tick",
        "args": {"executor": "copilot"},
        "requested_by": "cockpit",
        "created_at": "2026-07-03T09:00:00+00:00",
    }
    request.update(overrides)
    contract.atomic_write_json(constants.requests_dir() / f"{req_id}.json", request)
    return request


def _expected_backoff_attempt_clocks(tick_interval: float, count: int) -> list[float]:
    """Replicate the production backoff formula to compute expected attempt times."""
    clocks: list[float] = []
    elapsed = 0.0
    consecutive_failures = 0
    for _ in range(count):
        elapsed += manager_daemon._tick_backoff_seconds(tick_interval, consecutive_failures)
        clocks.append(elapsed)
        consecutive_failures += 1
    return clocks


def test_periodic_tick_backoff_prevents_hot_retry_and_resets_after_success(monkeypatch, tmp_path):
    monkeypatch.setenv("PSC_CONTROL_ROOT", str(tmp_path))
    clock = _FakeClock()
    call_clocks: list[float] = []

    def periodic_tick_runner() -> dict:
        call_clocks.append(clock.value)
        if len(call_clocks) <= 2:
            raise ValueError("boom")
        return {"dispatch_skipped": False}

    started = manager_daemon.run_loop(
        request_executor=lambda req: {"dispatched": []},
        status_provider=lambda: {"ready": [], "in_flight": [], "recent_done": []},
        periodic_tick_runner=periodic_tick_runner,
        poll_interval=1.0,
        tick_interval=10.0,
        now_fn=lambda: "2026-07-03T09:05:00+00:00",
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
        pid=1,
        max_rounds=85,
    )

    assert started is True
    # 1st attempt at t=10 (base tick_interval) fails; backoff to +20 -> 2nd
    # attempt at t=30 fails; backoff to +40 -> 3rd attempt at t=70 succeeds;
    # normal cadence resumes -> 4th attempt at t=80 (just +10, not +80).
    assert call_clocks == [10.0, 30.0, 70.0, 80.0]
    # 85 rounds at a 1s poll would be ~85 calls under the old hot-loop bug;
    # backoff keeps the call count nowhere near that.
    assert len(call_clocks) < 10

    status = contract.read_json(constants.status_path())
    assert status["daemon"]["consecutive_tick_failures"] == 0
    assert status["daemon"]["tick_circuit_open"] is False
    assert status["daemon"]["last_tick_error"] is None


def test_periodic_tick_circuit_breaker_stops_calls_but_keeps_draining_requests(monkeypatch, tmp_path):
    monkeypatch.setenv("PSC_CONTROL_ROOT", str(tmp_path))
    clock = _FakeClock()
    tick_interval = 1.0
    poll_interval = 1.0

    periodic_calls: list[float] = []

    def periodic_tick_runner() -> dict:
        periodic_calls.append(clock.value)
        raise ValueError("periodic tick always fails")

    processed_req_ids: list[str] = []
    seed_counter = {"n": 0}

    def request_executor(req: dict) -> dict:
        processed_req_ids.append(req["req_id"])
        seed_counter["n"] += 1
        _write_request(f"20260703T090000Z-seed{seed_counter['n']:05d}", type="dispatch")
        return {"dispatched": []}

    _write_request("20260703T090000Z-seed00000", type="dispatch")

    attempt_clocks = _expected_backoff_attempt_clocks(
        tick_interval, manager_daemon.TICK_CIRCUIT_BREAKER_THRESHOLD
    )
    max_rounds = int(attempt_clocks[-1]) + 10  # buffer, still far short of the cooldown

    started = manager_daemon.run_loop(
        request_executor=request_executor,
        status_provider=lambda: {"ready": [], "in_flight": [], "recent_done": []},
        periodic_tick_runner=periodic_tick_runner,
        poll_interval=poll_interval,
        tick_interval=tick_interval,
        now_fn=lambda: "2026-07-03T09:05:00+00:00",
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
        pid=1,
        max_rounds=max_rounds,
    )

    assert started is True
    # Circuit opens exactly at the threshold-th consecutive failure and stays
    # open for the (much longer) cooldown window, so no further periodic
    # attempts happen within this test's round budget.
    assert len(periodic_calls) == manager_daemon.TICK_CIRCUIT_BREAKER_THRESHOLD
    # The request queue (the operator rescue channel) drains one request per
    # round throughout -- entirely unaffected by the periodic circuit breaker.
    assert len(processed_req_ids) == max_rounds

    status = contract.read_json(constants.status_path())
    daemon = status["daemon"]
    assert daemon["tick_circuit_open"] is True
    assert daemon["consecutive_tick_failures"] == manager_daemon.TICK_CIRCUIT_BREAKER_THRESHOLD
    assert daemon["last_tick_error"]["type"] == "ValueError"


def test_status_reflects_tick_failure_and_resets_after_success(monkeypatch, tmp_path):
    monkeypatch.setenv("PSC_CONTROL_ROOT", str(tmp_path))

    def failing_runner() -> dict:
        raise ValueError("boom: sentinel reason")

    failure_points = iter([0.0, 5.0, 5.0])
    manager_daemon.run_loop(
        request_executor=lambda req: {"dispatched": []},
        status_provider=lambda: {"ready": [], "in_flight": [], "recent_done": []},
        periodic_tick_runner=failing_runner,
        poll_interval=0.0,
        tick_interval=5.0,
        now_fn=lambda: "2026-07-03T09:05:00+00:00",
        monotonic_fn=lambda: next(failure_points),
        sleep_fn=lambda _: None,
        pid=1,
        max_rounds=1,
    )

    status_after_failure = contract.read_json(constants.status_path())
    daemon_after_failure = status_after_failure["daemon"]
    assert daemon_after_failure["consecutive_tick_failures"] == 1
    assert daemon_after_failure["tick_circuit_open"] is False
    assert daemon_after_failure["last_tick_error"]["type"] == "ValueError"
    assert "sentinel reason" in daemon_after_failure["last_tick_error"]["reason"]
    assert daemon_after_failure["last_tick_at"] is None  # never succeeded yet

    success_points = iter([0.0, 5.0, 5.0])
    manager_daemon.run_loop(
        request_executor=lambda req: {"dispatched": []},
        status_provider=lambda: {"ready": [], "in_flight": [], "recent_done": []},
        periodic_tick_runner=lambda: {"dispatch_skipped": False},
        poll_interval=0.0,
        tick_interval=5.0,
        now_fn=lambda: "2026-07-03T09:06:00+00:00",
        monotonic_fn=lambda: next(success_points),
        sleep_fn=lambda _: None,
        pid=1,
        max_rounds=1,
    )

    status_after_success = contract.read_json(constants.status_path())
    daemon_after_success = status_after_success["daemon"]
    assert daemon_after_success["consecutive_tick_failures"] == 0
    assert daemon_after_success["tick_circuit_open"] is False
    assert daemon_after_success["last_tick_error"] is None
    assert daemon_after_success["last_tick_at"] == "2026-07-03T09:06:00+00:00"


def test_periodic_tick_cadence_unaffected_when_no_failures_occur(monkeypatch, tmp_path):
    monkeypatch.setenv("PSC_CONTROL_ROOT", str(tmp_path))
    clock = _FakeClock()
    call_clocks: list[float] = []

    def periodic_tick_runner() -> dict:
        call_clocks.append(clock.value)
        return {"dispatch_skipped": False}

    manager_daemon.run_loop(
        request_executor=lambda req: {"dispatched": []},
        status_provider=lambda: {"ready": [], "in_flight": [], "recent_done": []},
        periodic_tick_runner=periodic_tick_runner,
        poll_interval=1.0,
        tick_interval=10.0,
        now_fn=lambda: "2026-07-03T09:05:00+00:00",
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
        pid=1,
        max_rounds=35,
    )

    # Untouched regression: three ticks land exactly on tick_interval
    # multiples, with zero drift from the new backoff/circuit machinery.
    assert call_clocks == [10.0, 20.0, 30.0]


def test_log_error_deduplicates_repeated_signature_with_periodic_summary(capsys):
    manager_daemon._reset_log_error_dedup_state()
    exc = ValueError("same failure every time")
    total_calls = 220

    for _ in range(total_calls):
        manager_daemon._log_error(exc)

    output_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]

    interval = manager_daemon.LOG_ERROR_SUMMARY_INTERVAL
    expected_lines = 1 + (total_calls - 1) // interval
    assert len(output_lines) == expected_lines
    assert len(output_lines) < total_calls
    # First occurrence is always printed in full, never suppressed.
    assert "same failure every time" in output_lines[0]
    # At least one summary line proves the error is still recurring.
    assert any("repeated" in line and "same failure every time" in line for line in output_lines[1:])

    manager_daemon._log_error(RuntimeError("a totally different problem"))
    stderr_tail = capsys.readouterr().err
    assert "a totally different problem" in stderr_tail


def test_safe_tick_error_summary_redacts_paths_and_caps_length():
    exc = ValueError("failed reading /home/example-user/.agents/core/registry/db.sqlite during scan")

    summary = manager_daemon._safe_tick_error_summary(exc)

    assert summary["type"] == "ValueError"
    assert "/home" not in summary["reason"]
    assert "<path>" in summary["reason"]

    long_exc = RuntimeError("x" * 500)
    long_summary = manager_daemon._safe_tick_error_summary(long_exc)
    assert len(long_summary["reason"]) <= manager_daemon.TICK_ERROR_REASON_MAX_LENGTH + 1
