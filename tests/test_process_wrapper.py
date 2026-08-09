from __future__ import annotations

import json
import sys

from paulsha_cortex.coordinator import process_wrapper


def test_wrapper_records_child_exit_and_writes_empty_gate_ledger(tmp_path):
    sentinel = tmp_path / "job.exit"
    ledger = tmp_path / "job.gates.json"

    exit_code = process_wrapper.main(
        [
            "--sentinel",
            str(sentinel),
            "--ledger",
            str(ledger),
            "--worktree",
            str(tmp_path),
            "--run-gates",
            "--",
            sys.executable,
            "-c",
            "raise SystemExit(7)",
        ]
    )

    assert exit_code == 7
    assert sentinel.read_text(encoding="utf-8") == "7"
    assert json.loads(ledger.read_text(encoding="utf-8"))["gates"] == []
