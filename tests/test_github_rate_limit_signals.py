"""#370: rate limit must be classified before auth, even when the message
also contains "authenticate"/"OAuth" wording (GitHub's real secondary/
abuse-detection rate limit messages do exactly this)."""

from __future__ import annotations

import pytest

from paulsha_cortex.github_rate_limit import is_auth_signal, is_rate_limit_signal


@pytest.mark.parametrize(
    "message",
    [
        "HTTP 403: API rate limit exceeded for user ID 218201961",
        "You have exceeded a secondary rate limit for the OAuth App associated with this personal access token.",
        "You have triggered an abuse detection mechanism and have been temporarily blocked from content creation.",
        "HTTP 429 Too Many Requests",
        "X-RateLimit-Remaining: 0",
        "Retry-After: 120",
    ],
)
def test_is_rate_limit_signal_matches_known_github_wording(message: str) -> None:
    assert is_rate_limit_signal(message) is True


def test_secondary_rate_limit_message_also_matches_auth_pattern_alone() -> None:
    """Ground truth for the #370 bug: this exact message (real gh CLI output
    on a secondary/OAuth rate limit) contains "OAuth" and would be
    misclassified as an auth failure if auth is checked first/instead."""
    message = (
        "You have exceeded a secondary rate limit for the OAuth App associated "
        "with this personal access token. Please wait a few minutes before you "
        "try again by re-authenticating."
    )
    assert is_rate_limit_signal(message) is True
    # It legitimately also matches the (looser) auth pattern -- callers must
    # check rate-limit first and treat that as authoritative.
    assert is_auth_signal(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "HTTP 401: Bad credentials",
        "The token in ~/.config/gh/hosts.yml is invalid.",
        "You are not logged into any GitHub hosts. Run gh auth login to authenticate.",
    ],
)
def test_is_auth_signal_matches_real_credential_failures(message: str) -> None:
    assert is_auth_signal(message) is True


def test_pure_auth_failure_is_not_a_rate_limit_signal() -> None:
    assert is_rate_limit_signal("HTTP 401: Bad credentials") is False


def test_empty_or_missing_message_matches_neither() -> None:
    assert is_rate_limit_signal(None) is False
    assert is_rate_limit_signal("") is False
    assert is_auth_signal(None) is False
    assert is_auth_signal("") is False
