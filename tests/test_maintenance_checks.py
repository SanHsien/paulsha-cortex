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
    clean = upstream.render_markdown(sample_baseline(), [])
    failed = upstream.render_markdown(sample_baseline(), [], error="fetch failed")

    assert "No new upstream commits" in clean
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
