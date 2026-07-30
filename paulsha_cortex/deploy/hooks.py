"""reconcile 全域 agent hook 設定——只改寫 Cortex 自管的 managedBy entries。

issue #155：升級後 `$HOME/.codex/hooks.json` 仍保留舊版 psc-relay-hook.sh
絕對路徑（該檔案已隨舊 repo 佈局消失），造成 Codex Stop hook exit 127。
fresh install 的 template（`paulsha_cortex/scripts/hooks/codex.json`）已改用
`cortex relay-hook`，但 install/upgrade flow 從未 reconcile 既存的 live 設定。

本模組提供 idempotent 的 reconcile：只改寫 `managedBy` 標記為
`psc-coordinator-relay` 的 entries，其餘 owner（例如 `paulsha-memory`、
`psc-bro-return`）與未知 event 一律原樣保留。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from uuid import uuid4

MANAGED_BY = "psc-coordinator-relay"


@dataclass(frozen=True)
class HookReconcileResult:
    path: Path
    changed: bool
    migrated_events: tuple[str, ...] = field(default_factory=tuple)
    detail: str = ""


def _codex_hooks_manifest_path() -> Path:
    return Path(str(resources.files("paulsha_cortex") / "scripts" / "hooks" / "codex.json"))


def _load_canonical_commands(manifest_path: Path) -> dict[str, str]:
    """回傳 {event: canonical command}，例如 {"Stop": "PSC_RELAY_EVENT=stop cortex relay-hook"}。"""
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    commands: dict[str, str] = {}
    for event, groups in doc.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("managedBy") == MANAGED_BY and "command" in hook:
                    commands[event] = hook["command"]
    return commands


def default_codex_hooks_path(home: Path | None = None) -> Path:
    base = home if home is not None else Path.home()
    return base / ".codex" / "hooks.json"


def _atomic_write_text(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.parent / f".{target.name}.{uuid4().hex}.tmp"
    try:
        temp_path.write_text(text, encoding="utf-8")
        os.replace(temp_path, target)
    finally:
        temp_path.unlink(missing_ok=True)


def reconcile_codex_hooks(
    hooks_path: Path | None = None,
    *,
    manifest_path: Path | None = None,
) -> HookReconcileResult:
    """就地改寫 `hooks_path` 中屬於 `psc-coordinator-relay` 的 legacy entries。

    - 檔案不存在：no-op（fresh install 走既有 template 佈署路徑，不在此函式範圍）。
    - 非 managedBy=psc-coordinator-relay 的 entries：不動。
    - 已是 canonical command 的 entries：不動（idempotent，changed=False）。
    - 寫回前先備份原檔到 `<path>.bak-<hex>`，並以 atomic replace 落檔。
    """
    target = hooks_path if hooks_path is not None else default_codex_hooks_path()
    manifest = manifest_path if manifest_path is not None else _codex_hooks_manifest_path()

    if not target.is_file():
        return HookReconcileResult(path=target, changed=False, detail="hooks 設定不存在，略過")

    try:
        raw_text = target.read_text(encoding="utf-8")
        doc = json.loads(raw_text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return HookReconcileResult(
            path=target, changed=False, detail=f"hooks 設定無法解析，略過：{exc}"
        )

    if not isinstance(doc, dict) or not isinstance(doc.get("hooks"), dict):
        return HookReconcileResult(
            path=target, changed=False, detail="hooks 設定結構不符預期，略過"
        )

    canonical_commands = _load_canonical_commands(manifest)

    migrated_events: list[str] = []
    for event, canonical_command in canonical_commands.items():
        groups = doc["hooks"].get(event)
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            hooks = group.get("hooks")
            if not isinstance(hooks, list):
                continue
            for hook in hooks:
                if not isinstance(hook, dict):
                    continue
                if hook.get("managedBy") != MANAGED_BY:
                    continue
                if hook.get("command") == canonical_command:
                    continue
                hook["command"] = canonical_command
                if event not in migrated_events:
                    migrated_events.append(event)

    if not migrated_events:
        return HookReconcileResult(path=target, changed=False, detail="已是 canonical，無需遷移")

    backup_path = target.parent / f"{target.name}.bak-{uuid4().hex}"
    backup_path.write_text(raw_text, encoding="utf-8")

    new_text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    _atomic_write_text(target, new_text)

    return HookReconcileResult(
        path=target,
        changed=True,
        migrated_events=tuple(migrated_events),
        detail=f"遷移 {', '.join(migrated_events)} 至 cortex relay-hook；備份於 {backup_path}",
    )
