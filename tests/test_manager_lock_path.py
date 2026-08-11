from __future__ import annotations

import contextlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
START_SH = REPO / "paulsha_cortex" / "scripts" / "service-manager.sh"

# 只抽出 manager_lock_path 這個函式跑（比照 test_start_manager_service.py 的手法），
# 避免 source 整支 service-manager.sh 觸發其餘副作用。抽出範圍含它上方宣告的
# _psc_manager_lock_path 快取變數。
# NB: `}}` 是 Python str.format() 對字面 `}` 的跳脫；.format() 後 sed pattern
# 變成 /^}/，只配對行首（未縮排）的函式收尾大括號。
_HARNESS = """
set -euo pipefail
fn="$(sed -n '/^_psc_manager_lock_path=/,/^}}/p' "{start_sh}")"
eval "$fn"
manager_lock_path
{extra}
"""


@contextlib.contextmanager
def _tmp():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _run(env: dict, *, extra: str = "") -> subprocess.CompletedProcess:
    script = _HARNESS.format(start_sh=str(START_SH), extra=extra)
    full_env = {**os.environ, **env}
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=full_env)


def _write_python_stub(d: Path, argv_log: Path) -> str:
    """假的 `python3`：把 argv 記到 log，若被以 `-m paulsha_cortex.cli control
    lock-path` 呼叫則印出一個好認的路徑，讓測試能斷言 shell 真的委派給了它，
    而不是自己另外組一套硬寫規則。"""
    stub = d / "python3"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$*" >> "{argv_log}"\n'
        'if [[ "$1 $2 $3" == "-m paulsha_cortex.cli control" && "$4" == "lock-path" ]]; then\n'
        '  echo "/stub-control-root/${PSC_INSTANCE:-cortex}/manager.lock"\n'
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return str(stub)


class ManagerLockPathTests(unittest.TestCase):
    def test_delegates_to_python_control_contract(self) -> None:
        # #375：lock 路徑不得由 shell 自行硬寫（曾固定回退 $HOME/.agents/control，
        # 與 daemon 的 PSC_AGENTS_ROOT 解析鏈各自為政）；必須委派給
        # `cortex control lock-path`，兩端同源。
        with _tmp() as d:
            argv_log = d / "argv.log"
            py = _write_python_stub(d, argv_log)
            res = _run({"PY": py, "PSC_INSTANCE": "alpha"})
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(res.stdout.strip(), "/stub-control-root/alpha/manager.lock")
            self.assertIn(
                "-m paulsha_cortex.cli control lock-path",
                argv_log.read_text(encoding="utf-8"),
            )

    def test_result_is_cached_across_repeated_calls(self) -> None:
        """wait_for_manager_shutdown 最多輪詢 100 次；lock 路徑不會在同一次
        script 執行過程中變動，不該每次都重新 spawn python。"""
        with _tmp() as d:
            argv_log = d / "argv.log"
            py = _write_python_stub(d, argv_log)
            res = _run(
                {"PY": py, "PSC_INSTANCE": "alpha"},
                extra="manager_lock_path\nmanager_lock_path\n",
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            calls = [
                line for line in argv_log.read_text(encoding="utf-8").splitlines() if line.strip()
            ]
            self.assertEqual(len(calls), 1, f"expected exactly one python invocation, got {calls!r}")

    def test_two_instances_with_distinct_agents_root_get_distinct_lock_paths(self) -> None:
        """#375 驗收條件：兩個 instance 的 lock 檔不得為同一路徑。"""
        with _tmp() as d:
            argv_log = d / "argv.log"
            py = _write_python_stub(d, argv_log)
            first = _run({"PY": py, "PSC_INSTANCE": "alpha"})
            second = _run({"PY": py, "PSC_INSTANCE": "beta"})
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertNotEqual(first.stdout.strip(), second.stdout.strip())


if __name__ == "__main__":
    unittest.main()
