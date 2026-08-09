from __future__ import annotations

import re
from pathlib import Path, PurePosixPath, PureWindowsPath

_ABSOLUTE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]+|~[\\/]+|/)(?:[^\s'\"<>:]+[\\/]+)+[^\s'\"<>]*"
)


def is_absolute_any(value: str) -> bool:
    """Recognize POSIX and Windows absolute paths on every host OS."""
    return (
        Path(value).is_absolute()
        or PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).is_absolute()
    )


def has_parent_reference(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return ".." in PurePosixPath(normalized).parts


def redact_absolute_paths(value: str) -> str:
    return _ABSOLUTE_PATH_RE.sub("<path>", value)
