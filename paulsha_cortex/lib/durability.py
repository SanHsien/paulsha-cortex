from __future__ import annotations

import os
from pathlib import Path


def fsync_directory(directory: Path) -> None:
    """Persist directory metadata where the operating system supports it."""
    if os.name == "nt":
        return
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
