"""Cross-platform headless job wrapper.

Runs the model as typed argv, records its real exit code before deterministic
gates run, and never invokes a shell.  This is the native Windows counterpart
to the legacy Bash wrapper and is also safe to use on POSIX.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from paulsha_cortex.lib.durability import fsync_directory

from . import gate_ledger


def _write_exit_sentinel(path: Path, exit_code: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(str(exit_code))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paulsha-cortex-process-wrapper")
    parser.add_argument("--sentinel", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--run-gates", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(list(argv) if argv is not None else None)
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("missing child command")

    try:
        completed = subprocess.run(command, cwd=args.worktree, check=False)
        exit_code = int(completed.returncode)
    except OSError:
        exit_code = 127
    _write_exit_sentinel(Path(args.sentinel), exit_code)

    if args.run_gates:
        gate_ledger.main(
            ["--out", args.ledger, "--worktree", args.worktree]
        )
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
