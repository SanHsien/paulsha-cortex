"""Offline contract tests for the scheduled maintenance checkers in tools/."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_dependency_freshness as freshness  # noqa: E402
import check_upstream_updates as upstream  # noqa: E402

TOMLLIB_AVAILABLE = sys.version_info >= (3, 11)


def sample_baseline() -> dict:
    return {
        "repo": "https://example.invalid/upstream.git",
        "branch": "main",
        "reviewed_through": "a" * 40,
        "reviewed_date": "2026-08-12",
    }


def test_baseline_points_at_the_real_upstream() -> None:
    baseline = upstream.load_baseline()

    assert baseline["repo"].endswith("hamanpaul/paulsha-cortex.git")
    assert baseline["branch"] == "main"
    assert len(baseline["reviewed_through"]) == 40


def test_baseline_review_date_is_recorded_in_the_decision_log() -> None:
    baseline = upstream.load_baseline()
    decisions = (ROOT / "docs" / "UPSTREAM.md").read_text(encoding="utf-8")

    assert baseline["reviewed_date"] in decisions
    assert baseline["reviewed_through"] in decisions


def test_load_baseline_rejects_missing_invalid_and_incomplete_files(tmp_path: Path) -> None:
    with pytest.raises(upstream.UpstreamCheckError, match="missing baseline"):
        upstream.load_baseline(tmp_path / "missing.json")

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    with pytest.raises(upstream.UpstreamCheckError, match="invalid baseline"):
        upstream.load_baseline(invalid)

    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(json.dumps({"repo": "x"}), encoding="utf-8")
    with pytest.raises(upstream.UpstreamCheckError, match="missing fields"):
        upstream.load_baseline(incomplete)


def test_load_baseline_requires_a_full_sha(tmp_path: Path) -> None:
    baseline = sample_baseline()
    baseline["reviewed_through"] = "abc1234"
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(baseline), encoding="utf-8")

    with pytest.raises(upstream.UpstreamCheckError, match="40-character SHA"):
        upstream.load_baseline(path)


def test_upstream_report_states_clean_and_failed_runs() -> None:
    commit_mode = {**sample_baseline(), "track": "commit"}
    clean = upstream.render_markdown(commit_mode, [])
    failed = upstream.render_markdown(commit_mode, [], error="fetch failed")

    assert "No new upstream commits" in clean
    assert "Tracking: commit" in clean
    assert "Check failed" in failed
    assert "fetch failed" in failed


def test_upstream_report_escapes_pipes_and_caps_the_file_list() -> None:
    commits = [
        {
            "sha": "b" * 40,
            "short": "bbbbbbb",
            "date": "2026-08-13",
            "subject": "fix: demo | contract",
            "files": [f"paulsha_cortex/file_{index}.py" for index in range(10)],
        }
    ]

    report = upstream.render_markdown(sample_baseline(), commits)

    assert "1 upstream commit(s) require review" in report
    assert "fix: demo \\| contract" in report
    assert "+2 more" in report


def test_release_key_reads_the_release_segment_only() -> None:
    assert freshness.release_key("7.0.0rc1") == (7, 0, 0)
    assert freshness.release_key("6") == (6,)
    assert freshness.release_key("not-a-version") is None


def test_is_newer_version_compares_at_the_declared_precision() -> None:
    # ">=6" claims nothing about the minor, so 6.0.3 must not be reported.
    assert not freshness.is_newer_version("6.0.3", "6")
    assert freshness.is_newer_version("7.0.0", "6")
    assert freshness.is_newer_version("9.1.1", "8")
    assert freshness.is_newer_version("2.5.2", "1.26")
    assert not freshness.is_newer_version("1.26.4", "1.26")
    assert not freshness.is_newer_version("unknown", "1.26")


def test_parse_requirements_keeps_the_name_extras_and_floor() -> None:
    packages = freshness.parse_requirements(
        ["PyYAML>=6", "twine[keyring]>=6,<8", "pywin32>=306; sys_platform == 'win32'"],
        "runtime",
    )

    assert [package["name"] for package in packages] == ["PyYAML", "twine", "pywin32"]
    assert [package["minimum"] for package in packages] == ["6", "6", "306"]
    assert packages[0]["group"] == "runtime"


@pytest.mark.skipif(not TOMLLIB_AVAILABLE, reason="tomllib needs Python 3.11 or newer")
def test_load_direct_dependencies_covers_runtime_extras_and_build_backend() -> None:
    packages = freshness.load_direct_dependencies()
    groups = {package["group"] for package in packages}

    assert "runtime" in groups
    assert "build-system" in groups
    assert any(group.startswith("extra:") for group in groups)
    assert any(package["name"] == "PyYAML" for package in packages)


def test_load_direct_dependencies_reports_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(freshness.DependencyCheckError):
        freshness.load_direct_dependencies(tmp_path / "pyproject.toml")


def test_freshness_report_marks_each_status_and_reports_errors() -> None:
    rows: list[dict[str, object]] = [
        {
            "name": "pytest",
            "group": "extra:dev",
            "requirement": "pytest>=8",
            "minimum": "8",
            "latest": "9.1.1",
            "outdated": True,
            "check_failed": False,
        },
        {
            "name": "PyYAML",
            "group": "runtime",
            "requirement": "PyYAML>=6",
            "minimum": "6",
            "latest": "6.0.3",
            "outdated": False,
            "check_failed": False,
        },
    ]

    report = freshness.render_markdown(rows)
    failed = freshness.render_markdown([], error="cannot read pyproject.toml")

    assert "待審視" in report
    assert "| OK |" in report
    assert "檢查失敗" in failed
    assert "cannot read pyproject.toml" in failed


def test_parse_tag_refs_prefers_the_peeled_commit_and_sorts_by_version() -> None:
    raw = "\n".join(
        [
            "aaa\trefs/tags/v0.1.7",
            "bbb\trefs/tags/v0.1.7^{}",
            "ccc\trefs/tags/v0.1.10",
            "ddd\trefs/tags/v0.1.10^{}",
            "eee\trefs/tags/nightly-2026-08-22",
            "not-a-ref-line",
        ]
    )

    tags = upstream.parse_tag_refs(raw)

    # Annotated tags list the tag object first; the peeled line carries the commit.
    assert tags[0] == ((0, 1, 7), "v0.1.7", "bbb")
    # 0.1.10 outranks 0.1.7, which string sorting would get backwards.
    assert tags[-1] == ((0, 1, 10), "v0.1.10", "ddd")
    assert all("nightly" not in name for _, name, _ in tags)


def test_parse_tag_refs_tolerates_an_empty_listing() -> None:
    assert upstream.parse_tag_refs("") == []


def test_baseline_tracks_releases_because_this_fork_syncs_per_release() -> None:
    baseline = upstream.load_baseline()

    assert baseline["track"] == "release"
    assert baseline["reviewed_release"] == "v0.1.8"


def test_load_baseline_rejects_an_unknown_track_mode(tmp_path: Path) -> None:
    baseline = sample_baseline()
    baseline["track"] = "branch"
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(baseline), encoding="utf-8")

    with pytest.raises(upstream.UpstreamCheckError, match="track must be one of"):
        upstream.load_baseline(path)


def test_release_mode_report_distinguishes_quiet_from_a_new_release() -> None:
    baseline = sample_baseline()
    baseline["track"] = "release"
    baseline["reviewed_release"] = "v0.1.8"

    quiet = upstream.render_markdown(baseline, [])
    fired = upstream.render_markdown(
        baseline,
        [
            {
                "sha": "b" * 40,
                "short": "bbbbbbb",
                "date": "2026-09-01",
                "subject": "feat: something",
                "files": ["paulsha_cortex/cli.py"],
            }
        ],
        release="v0.1.9",
    )

    assert "No upstream release past the reviewed one" in quiet
    assert "Tracking: release" in quiet
    assert "(v0.1.8)" in quiet
    assert "Upstream released v0.1.9" in fired


def test_fork_status_counts_both_sides_of_the_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_git(args: list[str], repo_dir: Path) -> str:
        calls.append(args)
        if args[0] == "rev-list":
            return "56\n" if args[-1].endswith("..HEAD") else "202\n"
        if args[0] == "rev-parse":
            return "aaaaaaa\n" if args[-1] == "HEAD" else "bbbbbbb\n"
        raise AssertionError(f"unexpected git call: {args}")

    monkeypatch.setattr(upstream, "run_git", fake_git)
    status = upstream.fork_status(sample_baseline(), Path("."), "refs/upstream-check/main")

    assert status["ahead"] == 56
    assert status["behind"] == 202
    assert status["fork_head"] == "aaaaaaa"
    assert status["upstream_tip"] == "bbbbbbb"
    assert status["baseline"] == "a" * 7


def test_fork_status_is_reported_even_when_there_is_nothing_to_review() -> None:
    """The weekly quiet run should still say how far apart the two sides are."""
    baseline = {**sample_baseline(), "track": "release"}
    status = {
        "baseline": "dc8a968",
        "fork_head": "a8a6f9e",
        "upstream_tip": "13366c0",
        "ahead": 56,
        "behind": 202,
    }

    report = upstream.render_markdown(baseline, [], status=status)

    assert "No upstream release past the reviewed one" in report
    assert "ahead 56" in report
    assert "behind 202" in report


def test_a_fork_status_failure_does_not_masquerade_as_a_measurement() -> None:
    report = upstream.render_markdown(
        {**sample_baseline(), "track": "release"}, [], status_error="git rev-list failed"
    )

    assert "無法計算" in report
    assert "git rev-list failed" in report
    assert "ahead" not in report.split("## Fork status")[1]


# 紅燈的兩條正當出口：長期政策用 hold，這次不升用 deferral。
# 宣告是相容性承諾，不是消音鍵——調高下限讓報告變綠是被禁止的第三條路。


def test_hold_marker_binds_to_the_package_on_that_line() -> None:
    holds = freshness.parse_holds(
        'dependencies = ["PyYAML>=6"]  # freshness-hold: 6.x 就是我們要的下限\n'
        'other = ["pytest>=9.1"]\n'
    )

    assert holds == {"pyyaml": "6.x 就是我們要的下限"}


def test_a_comment_without_the_marker_is_not_a_hold() -> None:
    assert freshness.parse_holds('x = ["pytest>=9.1"]  # 一般註解\n') == {}


def test_deferral_without_a_reviewed_release_is_ignored(tmp_path: Path) -> None:
    # 沒有 deferredLatest 的條目等於永久靜音，不是延後，直接忽略。
    path = tmp_path / "deferrals.json"
    path.write_text(json.dumps({"deferrals": {"pytest": {"reason": "later"}}}), encoding="utf-8")

    assert freshness.load_deferrals(path) == {}


def test_deferral_with_a_reviewed_release_is_read(tmp_path: Path) -> None:
    path = tmp_path / "deferrals.json"
    path.write_text(
        json.dumps({"deferrals": {"pytest": {"deferredLatest": "9.1.1", "reason": "等 Windows gate"}}}),
        encoding="utf-8",
    )

    assert freshness.load_deferrals(path) == {"pytest": ("9.1.1", "等 Windows gate")}


def test_missing_deferrals_file_defers_nothing(tmp_path: Path) -> None:
    assert freshness.load_deferrals(tmp_path / "absent.json") == {}


def test_aged_floor_needs_review_unless_held_or_deferred() -> None:
    assert freshness.needs_review({"outdated": True, "hold": "", "deferred_reason": ""})
    assert not freshness.needs_review({"outdated": True, "hold": "政策", "deferred_reason": ""})
    assert not freshness.needs_review(
        {"outdated": True, "hold": "", "deferred_reason": "已評估，等下一輪"}
    )


def test_a_deferral_expires_once_pypi_moves_past_the_reviewed_release() -> None:
    deferrals = {"pytest": ("9.1.1", "等 Windows gate")}
    package = {"name": "pytest", "minimum": "9.0", "requirement": "pytest>=9.0", "group": "extra:test", "hold": ""}

    reviewed_release = freshness.is_newer_version("9.1.1", "9.1.1")
    next_release = freshness.is_newer_version("9.2.0", "9.1.1")

    assert not reviewed_release  # 停在被審視的那一版：延後仍然生效
    assert next_release  # 一往前推：延後失效，報告重新問
    assert deferrals["pytest"][1] == "等 Windows gate"
    assert package["hold"] == ""
