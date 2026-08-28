from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import stat

import yaml

CANONICAL_NAME = ".project-policy.yml"
LEGACY_NAME = ".paul-project.yml"
POLICY_NAMES = (CANONICAL_NAME, LEGACY_NAME)


class ProjectPolicyError(ValueError):
    """A project policy manifest cannot be selected authoritatively."""


@dataclass(frozen=True)
class ProjectPolicyResolution:
    path: Path | None
    payload: dict[str, object] | None
    legacy_only: bool = False
    dual_identical: bool = False


def _read_mapping(path: Path) -> dict[str, object]:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ProjectPolicyError(
            f"project policy unreadable: {path} ({type(exc).__name__})"
        ) from exc
    if stat.S_ISLNK(mode):
        raise ProjectPolicyError(f"project policy must not be a symlink: {path}")
    if not stat.S_ISREG(mode):
        raise ProjectPolicyError(f"project policy is not a regular file: {path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ProjectPolicyError(
            f"project policy unreadable: {path} ({type(exc).__name__})"
        ) from exc
    if not isinstance(payload, dict):
        raise ProjectPolicyError(f"project policy invalid: {path}")
    return payload


def read_project_policy_file(path: str | Path) -> dict[str, object]:
    """讀取一份明確指定的 policy candidate，沿用 canonical policy 的安全檢查。"""
    return _read_mapping(Path(path))


def resolve_project_policy(repo_root: str | Path) -> ProjectPolicyResolution:
    root = Path(repo_root)
    present: list[tuple[Path, dict[str, object]]] = []
    for name in POLICY_NAMES:
        path = root / name
        try:
            payload = _read_mapping(path)
        except FileNotFoundError:
            continue
        present.append((path, payload))

    if not present:
        return ProjectPolicyResolution(path=None, payload=None)
    if len(present) == 2 and present[0][1] != present[1][1]:
        raise ProjectPolicyError(
            "project policy conflict: .project-policy.yml and "
            ".paul-project.yml have different YAML semantics"
        )

    path, payload = present[0]
    return ProjectPolicyResolution(
        path=path,
        payload=payload,
        legacy_only=path.name == LEGACY_NAME,
        dual_identical=len(present) == 2,
    )
