from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path


def remove_tree(path: str | Path) -> None:
    """Remove a disposable tree, clearing Windows read-only attributes."""
    target = Path(path)
    if not target.exists() and not target.is_symlink():
        return

    def retry_readonly(function, value, _error):
        os.chmod(value, stat.S_IWRITE | stat.S_IREAD)
        function(value)

    shutil.rmtree(target, onexc=retry_readonly)
