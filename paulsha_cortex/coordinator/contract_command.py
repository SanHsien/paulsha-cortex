from __future__ import annotations

from typing import Mapping

from paulsha_cortex.persona import render
from paulsha_cortex.persona.contract import PersonaContract


def build_dispatch_prompt(
    role: str,
    *,
    task: str,
    plan_path: str,
    worktree_root: str | None = None,
    catalog: Mapping[str, PersonaContract] | None = None,
) -> str:
    """強制點 ①：把 persona 契約 render 成 executor-agnostic 純文字 prompt 前言。

    純字串函式、零 I/O：只嵌 plan_path 參照（agent 於 worktree 內自行讀計畫）。
    未知 role → ValueError（由 render_contract_prompt 冒泡）。
    不含任何 shell/executor 包裝；executor argv 由 AgentLauncher 各自組裝（launcher.py）。
    """
    contract_prompt = render.render_contract_prompt(role, catalog)
    boundary = ""
    if worktree_root is not None:
        boundary = (
            "\n[AUTHORITATIVE WORKTREE]\n"
            f"repository_root: {worktree_root}\n"
            "所有 repository 讀取、寫入與命令 MUST 使用此 root，或使用其下的相對路徑。\n"
            "operator/base checkout 不在本次 scope；禁止存取。若路徑被 sandbox 拒絕，"
            "請從目前 cwd 重新解析，不得重試被拒絕的絕對路徑。\n"
            "[END AUTHORITATIVE WORKTREE]\n"
        )
    return (
        f"{contract_prompt}\n\n"
        f"[TASK] {task}\n"
        f"[PLAN: {plan_path}]\n"
        f"{boundary}"
        "請於本 worktree 內讀取上述 plan 並依 persona 契約邊界執行。"
    )
