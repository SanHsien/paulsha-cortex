from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .compile import DeckCompileError, compile_combo, emit, specs_dir
from .schema import (
    DEFAULT_CARDS_PATH,
    DEFAULT_COMBOS_DIR,
    DeckSchemaError,
    iter_combo_files,
    load_cards,
    load_combo,
    resolve_combo_path,
)
from .verify import DeckVerifyError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cortex deck",
        description="將 Deck combo 編譯成預設 dispatch:hold 的 slice specs。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="列出 combo 與其卡片成員")
    list_parser.add_argument("combo", nargs="?", help="只列出指定 combo ID")

    compile_parser = sub.add_parser("compile", help="combo+task → slice specs（預設 dry-run）")
    compile_parser.add_argument("combo", help="combo ID（例如 feature-oneshot）")
    compile_parser.add_argument("--task", required=True, help="人類可讀的任務描述")
    compile_parser.add_argument(
        "--slug",
        help="覆寫 task slug（最多 60 字元，僅允許小寫英數與連字號）",
    )
    compile_parser.add_argument("--change", help="OpenSpec change ID；正式 emit 時依 combo 需求提供")
    compile_parser.add_argument("--with", dest="with_cards", action="append", default=[],
                                metavar="CARD[:after=ID|:before=ID]")
    compile_parser.add_argument("--only", nargs="+", default=[])
    compile_parser.add_argument("--allow-external", action="store_true", help="允許 combo 宣告的外部前置輸入")
    compile_parser.add_argument("--plan", dest="plan_ref", help="覆寫產生 spec 的 plan reference")
    compile_parser.add_argument(
        "--repo",
        help="從 claim/work item 顯式帶入的 owner/repo；省略時 spec 維持 repo: null",
    )
    compile_parser.add_argument(
        "--policy-from",
        help="從 repo 內相對路徑讀取本次 compile 要採用的候選 project policy",
    )
    out_group = compile_parser.add_mutually_exclusive_group()
    out_group.add_argument("--out", help="寫入指定 spec 目錄；未設定時只 dry-run")
    out_group.add_argument("--emit", action="store_true", help="寫入預設 specs 目錄；未設定時只 dry-run")
    compile_parser.add_argument("--force", action="store_true", help="允許覆寫既有輸出檔")

    verify_parser = sub.add_parser("verify", help="卡片 produces 存在性驗收")
    verify_parser.add_argument("card_id", help="要驗收 produces glob 的 card ID")
    verify_parser.add_argument("--task-slug", required=True, help="compile 輸出的 task slug")
    verify_parser.add_argument("--change", help="OpenSpec change ID")
    verify_parser.add_argument("--root", default=".", help="glob 驗收根目錄（預設：目前目錄）")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    try:
        cards = load_cards(DEFAULT_CARDS_PATH)
        if args.command == "list":
            combo_files = (
                [(args.combo, resolve_combo_path(args.combo, package_dir=DEFAULT_COMBOS_DIR))]
                if args.combo
                else list(iter_combo_files(package_dir=DEFAULT_COMBOS_DIR))
            )
            for _combo_id, combo_file in combo_files:
                combo = load_combo(combo_file, cards)
                band_cards = len(combo.band_triggered.cards) if combo.band_triggered else 0
                print(
                    f"{combo.id}\t(task_type={combo.task_type}, "
                    f"cards={len(combo.cards) + band_cards})"
                )
                for entry in combo.cards:
                    card = cards[entry.ref]
                    print(f"  card: {card.id}\t[{card.type}/{card.card_class}]")
                if combo.band_triggered is not None:
                    for entry in combo.band_triggered.cards:
                        card = cards[entry.ref]
                        print(
                            f"  card: {card.id}\t[{card.type}/{card.card_class}; "
                            f"band>={combo.band_triggered.trigger}]"
                        )
            if not args.combo:
                print("available cards:")
                for card in cards.values():
                    print(f"  card: {card.id}\t[{card.type}/{card.card_class}]")
            return 0

        if args.command == "compile":
            combo = load_combo(resolve_combo_path(args.combo, package_dir=DEFAULT_COMBOS_DIR), cards)
            effective_change = args.change
            if effective_change is None and not args.emit and not args.out:
                effective_change = "dry-run"
            result = compile_combo(
                combo,
                cards,
                args.task,
                change=effective_change,
                with_cards=tuple(args.with_cards),
                only=tuple(args.only),
                allow_external=args.allow_external,
                plan_ref=args.plan_ref,
                repo=args.repo,
                policy_from=args.policy_from,
                slug=args.slug,
            )
            if args.slug is None and any(not char.isascii() for char in args.task):
                print(
                    "deck compile: [WARNING] task 含非 ASCII 字元，自動 task-slug 可能失真；"
                    "請用 --slug <branch-safe-slug> 明確指定",
                    file=sys.stderr,
                )
            if args.repo is None and result.slices:
                print(
                    "deck compile: [WARNING] 未提供 --repo owner/repo；輸出 spec 會維持 repo: null，"
                    "不得由目錄或 Git remote 推斷歸屬",
                    file=sys.stderr,
                )
            print(f"task-slug: {result.task_slug}")
            print("前置 checklist（interactive）：")
            for line in result.checklist:
                print(f"  - {line}")
            if result.external:
                print("external inputs（已放行）：")
                for item in result.external:
                    print(f"  - {item}")
            if args.emit or args.out:
                target = specs_dir() if args.emit else args.out
                written = emit(result, target, force=args.force)
                resolved_target = Path(target).resolve()
                print(f"已寫入 {len(written)} 份輸出（dispatch: hold）")
                print(f"output-dir: {resolved_target}")
                for path in written:
                    print(f"  - {path.resolve()}")
                print("翻 auto 前先跑：")
                for command in result.verify_commands:
                    print(f"  - {command}")
            else:
                for slice_doc in result.slices:
                    print(f"--- {slice_doc.filename} ---")
                    print(slice_doc.content)
            return 0

        if args.command == "verify":
            from .verify import verify_card

            card = cards.get(args.card_id)
            if card is None:
                print(f"未知卡片: {args.card_id}", file=sys.stderr)
                return 2
            result = verify_card(card, args.task_slug, root=args.root, change=args.change)
            for missing in result.missing:
                print(f"MISSING {missing}")
            print("PASS" if result.ok else "FAIL")
            return 0 if result.ok else 1

        return 2
    except (DeckSchemaError, DeckCompileError, DeckVerifyError) as exc:
        print(f"deck: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
