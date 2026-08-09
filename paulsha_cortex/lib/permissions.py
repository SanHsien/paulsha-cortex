from __future__ import annotations

import os
import stat


def mode_matches(actual_mode: int, expected_mode: int) -> bool:
    """Compare POSIX modes without inventing unavailable Windows semantics."""
    actual = stat.S_IMODE(actual_mode)
    expected = stat.S_IMODE(expected_mode)
    if os.name != "nt":
        return actual == expected
    if expected & 0o222 == 0:
        return actual & 0o222 == 0
    return actual & 0o200 != 0
