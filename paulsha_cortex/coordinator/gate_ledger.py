"""#261：gate ledger writer——由 manager 掌控的 wrapper 執行，不由模型自述。

R2 的重驗只有在「被驗的東西不是模型講的話」時才有意義。本模組因此刻意**不**接受
任何來自模型輸出的資料：gate 清單由 operator 以 ``PSC_GATE_CMD_<NAME>`` 環境變數
宣告（與既有 ``PSC_PREFLIGHT_CMD`` 同一套 typed-argv 規範），命令由
:mod:`paulsha_cortex.coordinator.launcher` 產生的 wrapper script 在模型行程結束後
執行，exit code 由 shell／``subprocess`` 產生。模型既不能選擇要跑哪些 gate，也不能
決定 exit code，更不能在自己結束之後改寫 ledger。

wrapper 的形狀（見 ``launcher.build_wrapper_script``）：

.. code-block:: text

    <model argv>; printf %s "$?" > <sentinel>; python3 -m ...gate_ledger --out <ledger> ...

因為 ledger 是在模型結束**之後**才產生的，terminal envelope 內的 ``gate_evidence``
只能是模型「自述跑了哪些 gate、結果如何」的宣告；manager 用本模組獨立產生的 ledger
去對照那份宣告，任何不一致都是 R2 定義的矛盾。
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from . import terminal_contract


# operator 宣告 gate 的環境變數前綴；``PSC_GATE_CMD_PYTEST`` → gate ``pytest``。
GATE_ENV_PREFIX = "PSC_GATE_CMD_"

# 單一 gate 的預設逾時（秒）。逾時視同失敗，不得讓 job 無限期掛住。
DEFAULT_GATE_TIMEOUT_SECONDS = 1800
GATE_TIMEOUT_ENV = "PSC_GATE_TIMEOUT"

# 與 preflight._validate_typed_command 相同的紀律：不接受 shell wrapper，
# 避免 `bash -c "..."` 把任意字串重新變成可注入的 shell 片段。
_SHELL_EXECUTABLES = frozenset({"bash", "sh", "dash", "zsh", "ksh", "fish"})


class GateSpecError(ValueError):
    """gate 宣告本身不合法（operator 設定錯誤，不是模型的錯）。"""


@dataclass(frozen=True)
class GateSpec:
    """一個確定性 gate 的宣告。"""

    name: str
    argv: tuple[str, ...]

    @property
    def command(self) -> str:
        return shlex.join(self.argv)


def _validate_typed_command(name: str, command: Sequence[str]) -> None:
    if not command or any(not isinstance(item, str) or not item for item in command):
        raise GateSpecError(f"gate {name!r} 命令必須是非空 typed argv")
    index = 0
    if Path(command[0]).name == "env":
        index = 1
        while index < len(command) and (
            command[index].startswith("-") or "=" in command[index]
        ):
            index += 1
    if index < len(command) and Path(command[index]).name in _SHELL_EXECUTABLES:
        if "-c" in command[index + 1 :]:
            raise GateSpecError(f"gate {name!r} 不允許 shell wrapper")


def load_gate_specs(env: Mapping[str, str] | None = None) -> tuple[GateSpec, ...]:
    """從環境變數讀出 operator 宣告的 gate 清單（依 gate 名排序，確保確定性）。"""

    source = os.environ if env is None else env
    specs: list[GateSpec] = []
    for key in sorted(source):
        if not key.startswith(GATE_ENV_PREFIX):
            continue
        name = key[len(GATE_ENV_PREFIX) :].strip().lower()
        if not name:
            raise GateSpecError(f"gate 環境變數缺少名稱：{key}")
        raw = str(source[key]).strip()
        if not raw:
            # 空值等同「未宣告」，讓 operator 可以用空字串暫時停用某個 gate。
            continue
        try:
            argv = tuple(shlex.split(raw, posix=os.name != "nt"))
            if os.name == "nt":
                argv = tuple(
                    item[1:-1]
                    if len(item) >= 2 and item[0] == item[-1] and item[0] in {"'", '"'}
                    else item
                    for item in argv
                )
        except ValueError as exc:
            raise GateSpecError(f"gate {name!r} 命令無法解析") from exc
        _validate_typed_command(name, argv)
        specs.append(GateSpec(name=name, argv=argv))
    return tuple(specs)


def _gate_timeout(env: Mapping[str, str]) -> int:
    raw = str(env.get(GATE_TIMEOUT_ENV, "")).strip()
    if not raw:
        return DEFAULT_GATE_TIMEOUT_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_GATE_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_GATE_TIMEOUT_SECONDS


Runner = Callable[..., subprocess.CompletedProcess]


def run_gates(
    specs: Sequence[GateSpec],
    *,
    worktree: str | Path,
    timeout: int = DEFAULT_GATE_TIMEOUT_SECONDS,
    runner: Runner | None = None,
) -> list[dict[str, object]]:
    """實際執行每個 gate，回傳 ledger 的 ``gates`` 欄位內容。

    任何無法執行、逾時或非 0 exit code 一律記為 ``failed``——「跑不起來」不得被
    當成「通過」，否則 operator 設定壞掉會靜默變成 fail-open。
    """

    execute = subprocess.run if runner is None else runner
    rows: list[dict[str, object]] = []
    for spec in specs:
        try:
            completed = execute(
                list(spec.argv),
                cwd=str(worktree),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            exit_code = int(completed.returncode)
            detail = ""
            if exit_code != 0:
                stderr = (completed.stderr or "").strip()
                stdout = (completed.stdout or "").strip()
                detail = (stderr or stdout or f"exit_code={exit_code}")[-2000:]
        except subprocess.TimeoutExpired:
            exit_code = 124
            detail = f"gate timed out after {timeout}s"
        except (OSError, ValueError) as exc:
            exit_code = 127
            detail = f"gate command could not be executed: {exc}"
        rows.append(
            {
                "name": spec.name,
                "command": spec.command,
                "exit_code": exit_code,
                "status": "passed" if exit_code == 0 else "failed",
                "detail": detail,
            }
        )
    return rows


def build_ledger(
    gates: Sequence[Mapping[str, object]],
    *,
    slice_id: str | None = None,
) -> dict[str, object]:
    return {
        "schema_version": terminal_contract.GATE_LEDGER_SCHEMA_VERSION,
        "kind": terminal_contract.GATE_LEDGER_KIND,
        "slice_id": slice_id or "",
        "gates": [dict(row) for row in gates],
    }


def write_gate_ledger(
    *,
    ledger_path: str | Path,
    worktree: str | Path,
    env: Mapping[str, str] | None = None,
    runner: Runner | None = None,
) -> dict[str, object]:
    """執行宣告的 gate 並原子寫出 ledger；回傳寫出的 payload。

    即使沒有宣告任何 gate 也會寫出一份 ``gates: []`` 的 ledger——ledger 的**存在**
    本身就是「manager 掌控的 wrapper 確實跑完了」的證據，harvest 用它來區分
    「gate 全過」與「根本沒跑到」。
    """

    source = os.environ if env is None else env
    specs = load_gate_specs(source)
    gates = run_gates(
        specs,
        worktree=worktree,
        timeout=_gate_timeout(source),
        runner=runner,
    )
    payload = build_ledger(gates, slice_id=source.get("PSC_SLICE_ID"))
    target = Path(ledger_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(tmp, target)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paulsha-cortex-gate-ledger")
    parser.add_argument("--out", required=True, help="gate ledger 輸出路徑")
    parser.add_argument("--worktree", required=True, help="執行 gate 的工作目錄")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        write_gate_ledger(ledger_path=args.out, worktree=args.worktree)
    except GateSpecError:
        # operator 宣告錯誤：仍寫出一份「沒有任何 gate 通過」的 ledger，讓 harvest
        # fail closed 且訊息可追溯，而不是留下空目錄讓人以為 gate 沒被要求。
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(
                build_ledger(
                    [
                        {
                            "name": "gate-spec",
                            "command": "",
                            "exit_code": 78,
                            "status": "failed",
                            "detail": "PSC_GATE_CMD_* declaration is invalid",
                        }
                    ]
                ),
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        return 78
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI 進入點
    raise SystemExit(main())
