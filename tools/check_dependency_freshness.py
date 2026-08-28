"""Compare the dependencies declared in pyproject.toml against PyPI.

Dependabot proposes an upgrade when a package it watches publishes a release, but
it cannot answer the question a maintainer actually asks once a month: how far
behind is everything this repo declares? This reads every direct requirement --
runtime, optional extras, build backend -- asks PyPI for the current release, and
writes a Markdown report.

Declarations only. The installed environment is never inspected and no file is
ever edited: a newer release is a prompt to read the release notes and run the
suite, not a merge.

    python tools/check_dependency_freshness.py --output report.md --github-output
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "paulsha-cortex-dependency-freshness"

_REQUIREMENT_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*(.*)$")
_MINIMUM_RE = re.compile(r"(>=|>|==|~=)\s*([0-9][0-9A-Za-z.!+_-]*)")
_RELEASE_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)*")


class DependencyCheckError(RuntimeError):
    """Raised when pyproject.toml cannot be read."""


def _load_toml(path: Path) -> dict[str, Any]:
    # tomllib arrived in 3.11 and this package still supports 3.10, so the
    # import stays inside the one function that needs it. The scheduled check
    # runs on 3.13; on 3.10 only this call fails, not the whole module.
    try:
        import tomllib
    except ModuleNotFoundError as exc:  # pragma: no cover - 3.10 only
        raise DependencyCheckError(
            "reading pyproject.toml needs Python 3.11 or newer (tomllib)"
        ) from exc
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except OSError as exc:
        raise DependencyCheckError(f"cannot read {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise DependencyCheckError(f"invalid TOML in {path}: {exc}") from exc


def release_key(version: str) -> tuple[int, ...] | None:
    """Return the numeric release segment of a version, or None if unparsable.

    Pre-release and local suffixes are dropped, so 7.0.0rc1 and 7.0.0 rank the
    same -- precise enough for "has the declared floor aged?" without adding a
    PEP 440 parser to a package whose only runtime dependency is PyYAML.
    """
    match = _RELEASE_RE.match(version.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.group(0).split("."))


def is_newer_version(latest: str, declared: str) -> bool:
    """Is `latest` newer than `declared` at the precision `declared` states?

    A floor of `PyYAML>=6` says "any 6.x"; reporting 6.0.3 against it would be a
    standing false alarm, and a report that cries wolf every month gets ignored.
    So the comparison happens at the depth the declaration commits to: `>=6` is
    compared on the major alone, `>=1.26` on major and minor.
    """
    latest_key = release_key(latest)
    declared_key = release_key(declared)
    if latest_key is None or declared_key is None:
        return False
    depth = len(declared_key)
    padded = latest_key + (0,) * (depth - len(latest_key))
    return padded[:depth] > declared_key


def parse_requirements(requirements: list[str], group: str) -> list[dict[str, str]]:
    packages: list[dict[str, str]] = []
    for requirement in requirements:
        head = requirement.split(";", 1)[0]
        match = _REQUIREMENT_RE.match(head)
        if not match:
            continue
        name, specifiers = match.groups()
        minimum = _MINIMUM_RE.search(specifiers)
        packages.append(
            {
                "name": name,
                "minimum": minimum.group(2) if minimum else "",
                "requirement": requirement.strip(),
                "group": group,
            }
        )
    return packages


HOLD_MARKER = "freshness-hold:"
DEFERRALS_PATH = REPO_ROOT / ".github" / "dependency-deferrals.json"


def parse_holds(text: str) -> dict[str, str]:
    """Map package -> reason for ``# freshness-hold:`` comments in pyproject.toml.

    A hold is a standing policy, not a postponement: some floors are the floor we
    want, and re-asking every month turns the report into noise. tomllib drops
    comments, so the marker is read off the raw text of the declaring line.
    """
    holds: dict[str, str] = {}
    for line in text.splitlines():
        head, marker, comment = line.partition("#")
        reason = comment.strip()[len(HOLD_MARKER) :].strip()
        if not marker or not comment.strip().startswith(HOLD_MARKER) or not reason:
            continue
        for quoted in re.findall(r"\"([^\"]+)\"|'([^']+)'", head):
            match = _REQUIREMENT_RE.match(quoted[0] or quoted[1])
            if match:
                holds[match.group(1).lower()] = reason
    return holds


def load_deferrals(path: Path = DEFERRALS_PATH) -> dict[str, tuple[str, str]]:
    """Read reviewed-but-not-now decisions: package -> (reviewed release, reason).

    The reviewed release makes a deferral expire by itself: once PyPI moves past it
    the report asks again, so a deferral cannot quietly become a silenced check. An
    entry without it is ignored for exactly that reason.
    """
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get("deferrals", {})
    except (OSError, ValueError):
        return {}
    deferrals: dict[str, tuple[str, str]] = {}
    for name, entry in (entries or {}).items():
        if not isinstance(entry, dict):
            continue
        latest = str(entry.get("deferredLatest", "")).strip()
        reason = str(entry.get("reason", "")).strip()
        if latest and reason:
            deferrals[name.lower()] = (latest, reason)
    return deferrals


def needs_review(row: dict[str, Any]) -> bool:
    """An aged floor still counts unless a hold or a live deferral covers it."""
    return bool(row["outdated"]) and not row.get("hold") and not row.get("deferred_reason")


def load_direct_dependencies(
    pyproject_path: Path = REPO_ROOT / "pyproject.toml",
) -> list[dict[str, str]]:
    data = _load_toml(pyproject_path)
    holds = parse_holds(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    packages = parse_requirements(project.get("dependencies", []), "runtime")
    for extra, requirements in project.get("optional-dependencies", {}).items():
        packages.extend(parse_requirements(requirements, f"extra:{extra}"))
    packages.extend(
        parse_requirements(data.get("build-system", {}).get("requires", []), "build-system")
    )
    for package in packages:
        package["hold"] = holds.get(package["name"].lower(), "")
    return packages


def fetch_pypi_version(package_name: str, timeout: float = 10.0) -> str | None:
    quoted_name = urllib.parse.quote(package_name, safe="")
    request = urllib.request.Request(
        f"https://pypi.org/pypi/{quoted_name}/json",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    version = payload.get("info", {}).get("version")
    return str(version) if version else None


def collect_status(
    packages: list[dict[str, str]],
    deferrals: dict[str, tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    deferrals = deferrals if deferrals is not None else load_deferrals()
    rows: list[dict[str, Any]] = []
    for package in packages:
        minimum = package["minimum"]
        latest = fetch_pypi_version(package["name"])
        reviewed, reason = deferrals.get(package["name"].lower(), ("", ""))
        deferred = bool(reviewed and latest and not is_newer_version(latest, reviewed))
        rows.append(
            {
                **package,
                "latest": latest or "unknown",
                "outdated": bool(minimum and latest and is_newer_version(latest, minimum)),
                "check_failed": not minimum or latest is None,
                "hold": package.get("hold", ""),
                "deferred_reason": reason if deferred else "",
            }
        )
    return rows


def render_markdown(rows: list[dict[str, Any]], error: str | None = None) -> str:
    lines = ["# 依賴新鮮度報告", ""]
    if error:
        lines.extend(["## 檢查失敗", "", f"```text\n{error}\n```", ""])
        return "\n".join(lines)

    lines.extend(
        [
            "| 套件 | 群組 | 宣告 | PyPI 現行版 | 狀態 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        if row["check_failed"]:
            status = "檢查失敗"
        elif row["outdated"] and row.get("hold"):
            status = f"維持宣告：{row['hold']}"
        elif row["outdated"] and row.get("deferred_reason"):
            status = f"已延後（{row['latest']}）：{row['deferred_reason']}"
        elif row["outdated"]:
            status = "待審視"
        else:
            status = "OK"
        lines.append(
            f"| `{row['name']}` | `{row['group']}` | `{row['requirement']}` | "
            f"`{row['latest']}` | {status} |"
        )
    if not rows:
        lines.append("| - | - | - | - | 檢查失敗 |")
    lines.extend(
        [
            "",
            "本報告只比對 `pyproject.toml` 的宣告與 PyPI 現行版本，不檢查已安裝環境，",
            "也不會修改任何檔案。",
            "",
            "## 處理流程",
            "",
            "1. 讀 release notes，確認仍涵蓋 `requires-python` 宣告的 3.10–3.13。",
            "2. 在 Windows 原生與 Linux 兩邊跑 `python -m pytest tests -q` 再調宣告下限。",
            "3. 調整宣告屬 code change，需附 `changelog.d/` fragment。",
            "",
        ]
    )
    return "\n".join(lines)


def write_github_output(rows: list[dict[str, Any]], report_path: Path) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    outdated = any(needs_review(row) for row in rows)
    check_failed = not rows or any(bool(row["check_failed"]) for row in rows)
    with open(output_path, "a", encoding="utf-8") as output:
        output.write(f"outdated={'true' if outdated else 'false'}\n")
        output.write(f"check_failed={'true' if check_failed else 'false'}\n")
        output.write(f"needs_attention={'true' if outdated or check_failed else 'false'}\n")
        output.write(f"report_path={report_path.as_posix()}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="dependency-freshness-report.md")
    parser.add_argument("--github-output", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when a declared floor has aged.",
    )
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    error: str | None = None
    try:
        rows = collect_status(load_direct_dependencies())
    except DependencyCheckError as exc:
        error = str(exc)

    report = render_markdown(rows, error)
    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8")
    print(report)

    if args.github_output:
        write_github_output(rows, output_path)
    if error:
        return 2
    if args.strict and any(bool(row["outdated"]) or bool(row["check_failed"]) for row in rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
