"""`cortex control` 子命令：印出 control-plane 契約路徑。

issue #375：`service-manager.sh` 的 shell wrapper 過去硬寫一套 lock 路徑解析
（`${PSC_CONTROL_ROOT:-$HOME/.agents/control}/manager.lock`），而 Python daemon
走 `control/constants.py` → `config/runtime.py` 的完整解析鏈（explicit env →
PSC_AGENTS_ROOT → 已安裝 instance env → `$HOME/.agents`）。兩條路徑規則各自
硬寫，agents_root 不同時就會分歧——第二個 instance 的 daemon 啟動失敗，wrapper
卻認養到另一個 instance 的 pid，靜默降級成單 instance。

本模組是 shell 與 daemon 共用的單一來源：直接印出 `constants.lock_path()`，
不得另外重新實作一套路徑規則。
"""
from __future__ import annotations

import argparse
from typing import Sequence

from . import constants


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cortex control",
        description="印出 control-plane 契約路徑（與 manager daemon 使用同一套解析鏈）。",
    )
    sub = parser.add_subparsers(dest="target", required=True)
    sub.add_parser(
        "lock-path",
        help="印出 manager.lock 的絕對路徑（供 service-manager.sh 與 daemon 同源取用）",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.target == "lock-path":
        print(str(constants.lock_path()))
        return 0
    raise AssertionError("argparse must dispatch a known target")
