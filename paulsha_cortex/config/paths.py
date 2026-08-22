"""cortex 路徑契約——鏡射主 repo 治理平面所需的 paths 子集。"""
from __future__ import annotations

import os
from pathlib import Path

from .runtime import resolve_project_config_root, resolve_run_root, resolve_runtime_root


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name, "").strip()
    if not value:
        return None
    return Path(value).expanduser()


def _resolve_root(name: str, default: Path) -> Path:
    return _env_path(name) or default


def agents_root() -> Path:
    return resolve_runtime_root("PSC_AGENTS_ROOT")


def control_root() -> Path:
    return resolve_runtime_root("PSC_CONTROL_ROOT")


def coordinator_root() -> Path:
    return resolve_runtime_root("PSC_COORDINATOR_ROOT")


def specs_root() -> Path:
    return resolve_runtime_root("PSC_SPECS_ROOT")


def run_root() -> Path:
    return resolve_run_root()


def monitor_state_root() -> Path:
    """Durable Monitor state; distinct from the runtime socket directory."""
    return resolve_runtime_root("PSC_MONITOR_STATE_ROOT")


def work_items_snapshot_path() -> Path:
    return monitor_state_root() / "work-items.snapshot.json"


def skill_registry_root() -> Path:
    """Skill governance 治理平面根目錄（issue #204）：ledger／park state／proposal 共用。

    未宣告獨立 `PSC_*` override——沿用 `agents_root()`（已支援 `PSC_AGENTS_ROOT`
    覆寫）底下的 `registry` 子目錄，理由：這是 `~/.agents` 樹的 mutable runtime
    狀態，跟 coordinator/control/specs/monitor 屬同一族，沒必要另開一個環境變數
    造成 path 契約碎片化。
    """
    return agents_root() / "registry"


def skill_usage_ledger_path() -> Path:
    """Append-only skill usage event ledger（`schema_version`/`event_id`/... 見
    `paulsha_cortex.coordinator.skill_ledger`）。"""
    return skill_registry_root() / "skill_usage.jsonl"


def skill_park_state_path() -> Path:
    """目前已 park 的 skill 清單（可逆狀態，不含歷史紀錄／ledger 本身）。"""
    return skill_registry_root() / "skill_park.json"


def skill_park_proposals_root() -> Path:
    """Janitor 產生、尚待 operator 核准/已核准的 park proposal 檔案目錄。"""
    return skill_registry_root() / "skill_park_proposals"


def config_root() -> Path:
    return _resolve_root("PSC_CONFIG_ROOT", Path.home() / ".config" / "paulshaclaw")


def config_path(*parts: str) -> Path:
    return config_root().joinpath(*parts)


def project_config_root() -> Path:
    return resolve_project_config_root()


class RepoRootUnresolvedError(RuntimeError):
    """`PSC_REPO_ROOT` 未宣告，且呼叫端沒有顯式表態要用 cwd。

    刻意繼承 `RuntimeError` 而非 `ValueError`：daemon 的 tick isolation 攔的是
    `(ValueError, RuntimeError, OSError)`，兩者都在其中，但 `RuntimeError` 可與
    registry 那族「契約驗證失敗」的 `ValueError` 區分開來——這條不是資料不合法，
    是**執行環境沒有宣告目標 repo**。
    """


def configured_repo_root() -> Path | None:
    """只回 `PSC_REPO_ROOT` 顯式宣告的值；未宣告回 `None`（**不猜**）。

    舊實作的預設值是 `Path.cwd()`，於是「沒有宣告」與「宣告成當下工作目錄」在
    型別上無從分辨，呼叫端也就無從 fail-closed。把「有沒有宣告」這個資訊獨立
    出來，讓需要判斷的呼叫端能先問「宣告了嗎」再決定要不要走推斷。
    """
    return _env_path("PSC_REPO_ROOT")


def repo_root(*, allow_cwd: bool = False) -> Path:
    """本 instance 治理的目標 repo 根。**預設 fail-closed。**

    舊實作 `_resolve_root("PSC_REPO_ROOT", Path.cwd())` 在未宣告時靜默退回
    `Path.cwd()`，而 Windows service 的工作目錄正是 operator 的真實 checkout
    ——於是任何解析不出目標的呼叫（相對 spec 路徑、缺 env 的 unit）都不是失敗，
    而是**打在錯的樹上**：`git fetch`／`rev-parse`／`merge-base`／worktree 建立
    全部落到 operator 的工作區。

    需要 cwd 語意的呼叫端（operator 手動 CLI）必須顯式傳 `allow_cwd=True`——
    意圖寫在呼叫點上，不再由預設值默默生效。

    取自上游 `59a7a9b`（hamanpaul/paulsha-cortex#630 / #612）。本 fork 的
    `deploy/windows_service.py` 以 manifest 的 `repo_root` 啟動服務，正是這個
    失效模式的實例。
    """
    explicit = configured_repo_root()
    if explicit is not None:
        return explicit
    if allow_cwd:
        return Path.cwd()
    raise RepoRootUnresolvedError(
        "PSC_REPO_ROOT 未宣告，拒絕退回 cwd：production 動作必須有顯式的目標 "
        "repo 才能執行。請設定 PSC_REPO_ROOT，或由呼叫端顯式傳入 repo root；"
        "operator 手動 CLI 若確實要用當下工作目錄，請顯式傳 allow_cwd=True。"
    )


def _canonical_repo_root(repo: Path) -> Path:
    if repo.parent.name == ".worktrees":
        return repo.parent.parent
    return repo


def worktree_root_for(repo: Path) -> Path:
    """依給定 repo 計算 worktree pool，預設為 sibling `<repo>-worktrees`。"""
    override = _env_path("PSC_WORKTREE_ROOT")
    if override is not None:
        return override
    repo = _canonical_repo_root(repo)
    return repo.parent / f"{repo.name}-worktrees"


def worktree_root() -> Path:
    """coordinator 派工 worktree pool 的預設路徑。"""
    return worktree_root_for(repo_root())
