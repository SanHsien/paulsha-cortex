"""#452 A：`cortex model profile` porcelain 入口（呈現層；核心邏輯在
coordinator.model_profile）。patchmud 不在場時印明確 skip 訊息並回 0。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from paulsha_cortex.coordinator.model_profile import (
    DEFAULT_DECK_ID,
    ProfileOptions,
    run_model_profile,
)

from . import COMMANDS, PorcelainCommand, register

MODEL_PROFILE_SCHEMA = "cortex-porcelain/model-profile/v1"


def register_commands() -> None:
    if "model" in COMMANDS:
        return
    register(
        PorcelainCommand(
            name="model",
            help="模型能力側寫：patchmud 一次性評測 → 封套 diff 預覽／--apply 落地",
            run=main,
        )
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cortex model")
    sub = parser.add_subparsers(dest="command", required=True)

    profile = sub.add_parser(
        "profile",
        help="對 registry 內 source=default 的身分跑 patchmud deck，產封套 diff 預覽",
    )
    profile.add_argument("--apply", action="store_true", help="經人工複核後把實測封套寫入 packaged registry 檔")
    profile.add_argument("--force", action="store_true", help="忽略評測指紋，強制重評")
    profile.add_argument("--deck", default=DEFAULT_DECK_ID, help="deck id（預設 pilot-v1）")
    profile.add_argument("--patchmud-bin", default=None, help="patchmud 可執行檔路徑（預設 PATH 查找）")
    profile.add_argument("--patchmud-root", default=None, help="patchmud repo 根（預設 $HOME/prj_pri/paulsha-patchmud 或 PSC_PATCHMUD_ROOT）")
    profile.add_argument("--registry-file", default=None, help="registry 寫入目標（預設 packaged data/model-identities.yaml）")
    profile.add_argument(
        "--identity",
        action="append",
        default=[],
        help="只處理指定身分（executor/model_id，可重複）",
    )
    profile.add_argument("--json", action="store_true", help="輸出 cortex-porcelain/model-profile/v1 JSON")
    return parser


def _print_text(result: dict[str, Any]) -> None:
    skip_reason = result.get("skip_reason")
    if skip_reason == "patchmud-not-found":
        sys.stdout.write(
            "skip: 找不到 patchmud 可執行檔——評測巷道為選配，維持保守預設封套"
            "（安裝 patchmud 後重跑 `cortex model profile`）\n"
        )
        return
    if skip_reason == "patchmud-version-unresolvable":
        sys.stdout.write(
            "skip: 無法解析 patchmud 版本（patchmud root 缺 VERSION）——評測指紋"
            "需要版本成分，維持保守預設封套\n"
        )
        return
    patchmud = result.get("patchmud") or {}
    deck = patchmud.get("deck") or {}
    sys.stdout.write(
        f"patchmud: {patchmud.get('bin')} v{patchmud.get('version')} "
        f"deck={deck.get('deck_id')} encounters={deck.get('encounter_count')} "
        f"sha256={str(deck.get('content_sha256'))[:12]}…\n"
    )
    for cell in result.get("cells", []):
        label = f"{cell.get('executor')}/{cell.get('model_id')} {cell.get('persona')}"
        status = cell.get("status")
        line = f"{status:>16}  {label}: {cell.get('reason', '-')}"
        detail = cell.get("detail")
        if detail:
            line += f"（{detail}）"
        sys.stdout.write(line + "\n")
        for failure in cell.get("encounter_failures", []) or []:
            sys.stdout.write(f"                  encounter 失敗：{failure}\n")
        diff = cell.get("diff")
        if diff:
            sys.stdout.write(diff if diff.endswith("\n") else diff + "\n")
    if result.get("applied"):
        sys.stdout.write(
            f"已寫入 {result.get('registry_file')}——請檢視 git diff 後自行 commit。\n"
        )
    elif any(cell.get("status") == "proposed" for cell in result.get("cells", [])):
        sys.stdout.write("未帶 --apply：以上僅為 diff 預覽，registry 未寫入。\n")


def main(argv: Sequence[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv))
    if args.command != "profile":  # pragma: no cover - argparse required=True 已擋
        parser.error(f"unsupported model command: {args.command}")
    options = ProfileOptions(
        apply=args.apply,
        force=args.force,
        deck_id=args.deck,
        patchmud_bin=args.patchmud_bin,
        patchmud_root=Path(args.patchmud_root) if args.patchmud_root else None,
        registry_file=Path(args.registry_file) if args.registry_file else None,
        identity_filter=tuple(args.identity),
    )
    try:
        result = run_model_profile(options)
    except ValueError as exc:
        print(f"錯誤: {exc}", file=sys.stderr)
        return 2
    if args.json:
        payload = {"schema": MODEL_PROFILE_SCHEMA, "result": result}
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    else:
        _print_text(result)
    if any(cell.get("status") == "failed" for cell in result.get("cells", [])):
        return 1
    return 0
