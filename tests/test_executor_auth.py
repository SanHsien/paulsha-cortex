"""#369：`coordinator.executor_auth` 的分類與探測行為測試。

這個模組是 `porcelain/bootstrap.py` 的 copilot rate-limit 誤判修復與
`runtime_preflight.py` 的 `provider:executor` sentinel 共用的分類邏輯——
兩處分開實作、各自漂移正是 #369 想避免的。
"""

from __future__ import annotations

import subprocess

import pytest

from paulsha_cortex.coordinator.executor_auth import (
    EXECUTOR_CANDIDATES,
    check_executor_auth,
    classify_cli_output,
)


# --------------------------------------------------------------- classify_cli_output


def test_classify_returncode_zero_is_always_ok():
    status, _ = classify_cli_output(0, "irrelevant noise mentioning login and rate limit")
    assert status == "ok"


@pytest.mark.parametrize(
    "output",
    [
        "Error: secondary rate limit exceeded. Please wait and try again.",
        "You have exceeded a rate limit. Try again later.",
        "abuse detection mechanism triggered",
        "HTTP 429 Too Many Requests",
        "HTTP 403 Forbidden",
        "X-RateLimit-Remaining: 0",
        "Retry-After: 60",
        "quota exceeded for this billing period",
        "usage limit reached",
    ],
)
def test_classify_rate_limit_signals(output: str):
    status, _ = classify_cli_output(1, output)
    assert status == "rate_limited"


def test_classify_rate_limit_wins_over_login_wording():
    """#369 核心案例：GitHub 的限流訊息常常同時帶有 "authenticate"／"login"
    字樣（例如「請重新授權以取得更高額度」），rate limit 判定必須排在前面，
    否則會被誤判成登出——這正是 bootstrap.py 修復前的實際 bug。
    """

    output = (
        "Error: You have exceeded a secondary rate limit. "
        "To authenticate again, please run `copilot /login`."
    )
    status, _ = classify_cli_output(1, output)
    assert status == "rate_limited"


@pytest.mark.parametrize(
    "output",
    [
        "please run copilot login",
        "Error: not authenticated. Run `claude auth login`.",
        "authorization required",
        "please complete the device code flow",
    ],
)
def test_classify_login_signals_without_rate_limit_wording(output: str):
    status, _ = classify_cli_output(1, output)
    assert status == "logged_out"


def test_classify_unknown_when_no_signal_matches():
    status, detail = classify_cli_output(1, "boom: unexpected internal error")
    assert status == "unknown"
    assert "exit 1" in detail


def test_classify_handles_empty_output():
    status, _ = classify_cli_output(1, "")
    assert status == "unknown"


# ---------------------------------------------------------------- check_executor_auth


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["stub"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_check_executor_auth_ok():
    def _runner(argv, *, timeout):
        assert argv[0] == "claude"
        return _completed(0)

    result = check_executor_auth(
        "claude", executable="claude", runner=_runner, now=lambda: 1234.0
    )
    assert result.provider_id == "claude"
    assert result.status == "ok"
    assert result.reason is None
    assert result.observed_at == 1234.0


def test_check_executor_auth_uses_explicit_claude_executable():
    calls = []

    def _runner(argv, *, timeout):
        calls.append(tuple(argv))
        return _completed(0)

    result = check_executor_auth(
        "claude",
        executable="/opt/cortex/bin/claude-compatible",
        runner=_runner,
        now=lambda: 1234.0,
    )

    assert result.status == "ok"
    assert calls == [("/opt/cortex/bin/claude-compatible", "auth", "status")]


def test_check_executor_auth_invalid_override_never_calls_path_fallback(monkeypatch):
    monkeypatch.setenv("PSC_CLAUDE_EXECUTABLE", "claude-alias")
    calls = []

    def _runner(argv, *, timeout):
        calls.append(tuple(argv))
        return _completed(0)

    result = check_executor_auth(
        "claude", runner=_runner, now=lambda: 1234.0
    )

    assert result.status == "degraded"
    assert "absolute path" in (result.reason or "")
    assert calls == []


def test_check_executor_auth_logged_out():
    def _runner(argv, *, timeout):
        return _completed(1, stderr="please run codex login")

    result = check_executor_auth("codex", runner=_runner, now=lambda: 1234.0)
    assert result.status == "degraded"
    assert "codex" in result.reason
    assert "login" in result.reason.lower()


def test_check_executor_auth_rate_limited_is_not_logged_out():
    def _runner(argv, *, timeout):
        return _completed(
            1,
            stderr="secondary rate limit exceeded; to authenticate again, run copilot /login",
        )

    result = check_executor_auth("copilot", runner=_runner, now=lambda: 1234.0)
    assert result.status == "degraded"
    assert "rate limit" in result.reason.lower()
    # rate-limit 判定必須贏過 login 判定：reason 必須標成 rate limit 訊號，
    # 不能落到「no definitive signal」或被誤標成 logged-out。
    assert "no definitive signal" not in result.reason.lower()


def test_check_executor_auth_handles_missing_binary():
    def _runner(argv, *, timeout):
        raise FileNotFoundError("no such file")

    result = check_executor_auth(
        "claude", executable="claude", runner=_runner, now=lambda: 1234.0
    )
    assert result.status == "degraded"
    assert "FileNotFoundError" in result.reason


def test_check_executor_auth_handles_timeout():
    def _runner(argv, *, timeout):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)

    result = check_executor_auth("codex", runner=_runner, now=lambda: 1234.0)
    assert result.status == "degraded"
    assert "TimeoutExpired" in result.reason


def test_check_executor_auth_rejects_unsupported_executor():
    result = check_executor_auth("gemini", now=lambda: 1234.0)
    assert result.status == "degraded"
    assert "unsupported executor" in result.reason


def test_executor_candidates_matches_bootstrap_convention():
    assert set(EXECUTOR_CANDIDATES) == {"claude", "codex", "copilot"}
