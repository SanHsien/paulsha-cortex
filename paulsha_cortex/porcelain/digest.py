from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from paulsha_cortex.coordinator.digest import (
    DigestDeliveryError,
    emit_digest,
    render_digest_text,
)

from . import COMMANDS, PorcelainCommand, register


def register_commands() -> None:
    if "digest" in COMMANDS:
        return
    register(
        PorcelainCommand(
            name="digest",
            help="組裝並投遞 manager status digest（供排程觸發，見 emit）",
            run=main,
        )
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cortex digest")
    sub = parser.add_subparsers(dest="command", required=True)

    emit = sub.add_parser(
        "emit",
        help=(
            "讀取 manager status、組裝 digest 並投遞——"
            "預設寫檔案 outbox；PSC_DIGEST_DELIVERY_CMD 設定時改 pipe 給該命令"
        ),
    )
    emit.add_argument("--json", action="store_true", help="輸出 cortex-coordinator/digest/v1 JSON envelope")
    return parser


def _json_dump(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _run_emit(*, json_output: bool) -> int:
    try:
        envelope = emit_digest()
    except (ValueError, DigestDeliveryError) as exc:
        sys.stderr.write(f"錯誤: {exc}\n")
        return 1
    if json_output:
        _json_dump(envelope)
        return 0
    sys.stdout.write(render_digest_text(envelope["digest"]) + "\n")
    delivery = envelope.get("delivery", {})
    method = delivery.get("method")
    if method == "file":
        sys.stdout.write(f"delivered: file -> {delivery.get('path')}\n")
    elif method == "command":
        sys.stdout.write(f"delivered: command -> {' '.join(delivery.get('command', []))}\n")
    return 0


def main(argv: Sequence[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv))
    if args.command == "emit":
        return _run_emit(json_output=args.json)
    parser.error(f"unsupported digest command: {args.command}")
    return 2
