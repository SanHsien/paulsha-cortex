from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "docs" / "intent-contract.md"
EXAMPLE_PATH = REPO_ROOT / "examples" / "intent" / "sample-change" / "intent.md"
REQUIRED_HEADINGS = (
    "Problem",
    "Proposed outcome",
    "Affected users and systems",
    "Constraints",
    "Out of scope",
    "Evidence and sources",
    "Open questions",
    "Success signals",
)
WORK_ITEM_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _read(path: Path) -> str:
    assert path.is_file(), f"{path.relative_to(REPO_ROOT)} is missing"
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> dict[str, object]:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, flags=re.DOTALL)
    assert match is not None, "intent example must start with YAML frontmatter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict), "intent frontmatter must be a mapping"
    return data


def test_intent_example_matches_v1_contract() -> None:
    example = _read(EXAMPLE_PATH)
    metadata = _frontmatter(example)

    assert set(metadata) == {"schema", "work_item", "status", "owner"}
    assert metadata["schema"] == "cortex-intent/v1"
    assert metadata["status"] == "draft", "the distributable example must not self-approve"
    assert isinstance(metadata["owner"], str) and metadata["owner"].strip()
    assert isinstance(metadata["work_item"], str) and WORK_ITEM_RE.fullmatch(metadata["work_item"])
    for heading in REQUIRED_HEADINGS:
        assert f"## {heading}\n" in example, f"intent example is missing `{heading}`"


def test_contract_keeps_intent_separate_from_dispatch_authority() -> None:
    contract = _read(CONTRACT_PATH)
    for marker in (
        "exact Git commit SHA",
        "status: accepted",
        "不構成派工授權",
        "confirmed Todo",
        "不新增 CLI intake 行為",
    ):
        assert marker in contract, f"intent contract must preserve `{marker}`"


def test_lifecycle_and_discovery_docs_link_the_contract() -> None:
    lifecycle = _read(REPO_ROOT / "docs" / "unified-work-lifecycle.md")
    concepts = _read(REPO_ROOT / "docs" / "onboarding" / "concepts.md")
    readme = _read(REPO_ROOT / "README.md")

    assert "[Cortex Intent Contract v1](intent-contract.md)" in lifecycle
    assert "現行 CLI 不接受 `kind=intent`" in lifecycle
    assert "[Cortex Intent Contract v1](../intent-contract.md)" in concepts
    assert "[Intent contract](docs/intent-contract.md)" in readme
