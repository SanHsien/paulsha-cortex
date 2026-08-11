"""issue #395（continuation/adoption 型 slice 設計，見
`docs/superpowers/specs/continuation-adoption-dispatch-{spec,design}.md`）
本票唯一落地的 code 骨架：偵測某 worktree 是否處於進行中的 merge（`MERGE_HEAD`
存在）。

刻意最小、唯讀：只讀 `MERGE_HEAD`／`git status --porcelain=v2`，不驅動任何
write 動作（不 commit／不 abort／不 resolve conflict），也不接上
dispatch／gate／registry 任何既有機制。「偵測結果如何影響 completion
gate」「build card prompt 如何指示『完成 merge 而非 abort』」留給後續實作票
（design 文件 D4／D5，`tasks.md` 「後續應拆分的 code 票」段）。

`--git-path MERGE_HEAD` 對 git worktree 正確解析到該 worktree 私有的
`<main-repo>/.git/worktrees/<name>/MERGE_HEAD`（而非任何共用 `.git` 目錄），
已以真實 `git worktree add` 手動核驗；對一般（非 worktree）repo 回傳的路徑
相對於 `-C` 指定的目錄，兩種情況本模組皆正確處理（見 `detect_merge_state`
docstring）。
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# git_runner seam：收 argv（不含 "git"/"-C" 前綴），回 stdout 文字；失敗 raise。
# 與 dispatcher.GitRunner／autonomy 既有慣例同型。
GitRunner = Callable[[list[str]], str]


@dataclass(frozen=True)
class MergeState:
    """`detect_merge_state()` 的唯讀結果快照。"""

    in_progress: bool
    merge_head: str | None = None
    unmerged_paths: tuple[str, ...] = ()


def _default_git_runner(worktree: Path) -> GitRunner:
    def runner(args: list[str]) -> str:
        proc = subprocess.run(
            ["git", "-C", str(worktree), *args],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"git -C {worktree} {' '.join(args)} 失敗: {proc.stderr.strip()}"
            )
        return proc.stdout

    return runner


def _parse_unmerged_paths(porcelain_v2: str) -> tuple[str, ...]:
    """`git status --porcelain=v2` 的 `u ...`（unmerged/衝突）行 → 路徑 tuple。

    格式固定 11 欄：`u <XY> <sub> <m1> <m2> <m3> <mW> <h1> <h2> <h3> <path>`
    （已以真實衝突 fixture 核驗，見 `tests/test_mid_merge.py`）；`maxsplit=10`
    讓含空白的檔名仍完整落在最後一欄，不被截斷。
    """
    paths: list[str] = []
    for line in porcelain_v2.splitlines():
        if not line.startswith("u "):
            continue
        fields = line.split(maxsplit=10)
        if len(fields) == 11:
            paths.append(fields[10])
    return tuple(paths)


def detect_merge_state(
    worktree: str | Path,
    *,
    git_runner: GitRunner | None = None,
) -> MergeState:
    """讀 `<worktree>` 是否有進行中的 merge。

    純唯讀：只呼叫 `git rev-parse --git-path MERGE_HEAD`／`git status
    --porcelain=v2`，不執行任何寫入（不 commit／不 abort／不 resolve）。

    `git_runner` 未注入時對 `worktree` 跑真實 git 子行程；任一步驟失敗
    （非 git repo、路徑不存在、git 不可執行等）保守回傳
    `MergeState(in_progress=False)`——本函式 fail-open（讀不到就當作沒有進行
    中的 merge），不 raise，因為它只是一個觀測 helper；真正的安全性判斷仍在
    既有 `run_result_verification` 的 dirty-tree／ancestry 檢查（見 design
    文件 D5：「abort 一個進行中的 merge」在既有 ancestry 不變量下已經會被
    `candidate-not-descendant` 擋下，不依賴本函式的偵測結果）。
    """
    resolved = Path(worktree)
    runner = git_runner or _default_git_runner(resolved)
    try:
        merge_head_path_text = runner(["rev-parse", "--git-path", "MERGE_HEAD"]).strip()
    except Exception:
        return MergeState(in_progress=False)
    if not merge_head_path_text:
        return MergeState(in_progress=False)
    merge_head_path = Path(merge_head_path_text)
    if not merge_head_path.is_absolute():
        # 一般（非 worktree）repo：`--git-path` 回傳相對於 `-C` 目錄的路徑。
        merge_head_path = resolved / merge_head_path
    if not merge_head_path.is_file():
        return MergeState(in_progress=False)
    try:
        merge_head_sha = merge_head_path.read_text(encoding="utf-8").strip() or None
    except OSError:
        merge_head_sha = None
    try:
        status_text = runner(["status", "--porcelain=v2"])
    except Exception:
        status_text = ""
    return MergeState(
        in_progress=True,
        merge_head=merge_head_sha,
        unmerged_paths=_parse_unmerged_paths(status_text),
    )
