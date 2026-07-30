from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from paulsha_cortex.deploy import hooks as hooks_mod

LEGACY_STOP_COMMAND = (
    "PSC_RELAY_EVENT=stop $HOME/prj_pri/paulshaclaw/scripts/coordinator/psc-relay-hook.sh"
)
LEGACY_SESSION_START_COMMAND = (
    "PSC_RELAY_EVENT=session_start "
    "$HOME/prj_pri/paulshaclaw/scripts/coordinator/psc-relay-hook.sh"
)
CANONICAL_STOP_COMMAND = "PSC_RELAY_EVENT=stop cortex relay-hook"
CANONICAL_SESSION_START_COMMAND = "PSC_RELAY_EVENT=session_start cortex relay-hook"


def _legacy_doc() -> dict:
    return {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|clear|compact",
                    "hooks": [
                        {
                            "command": LEGACY_SESSION_START_COMMAND,
                            "type": "command",
                            "managedBy": "psc-coordinator-relay",
                        }
                    ],
                }
            ],
            "Stop": [
                {
                    "matcher": ".*",
                    "hooks": [
                        {
                            "command": "PSC_RELAY_EVENT=stop /some/other/psc-bro-return.sh",
                            "type": "command",
                            "managedBy": "psc-bro-return",
                        },
                        {
                            "command": LEGACY_STOP_COMMAND,
                            "type": "command",
                            "managedBy": "psc-coordinator-relay",
                        },
                    ],
                }
            ],
        }
    }


class HookReconcileTests(unittest.TestCase):
    def test_migrates_legacy_managed_entries_to_canonical_command(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "hooks.json"
            target.write_text(json.dumps(_legacy_doc()), encoding="utf-8")

            result = hooks_mod.reconcile_codex_hooks(target)

            self.assertTrue(result.changed)
            self.assertEqual(set(result.migrated_events), {"SessionStart", "Stop"})

            doc = json.loads(target.read_text(encoding="utf-8"))
            stop_hooks = doc["hooks"]["Stop"][0]["hooks"]
            session_hooks = doc["hooks"]["SessionStart"][0]["hooks"]
            self.assertEqual(session_hooks[0]["command"], CANONICAL_SESSION_START_COMMAND)
            managed_stop = next(h for h in stop_hooks if h["managedBy"] == "psc-coordinator-relay")
            self.assertEqual(managed_stop["command"], CANONICAL_STOP_COMMAND)

    def test_preserves_unrelated_owner_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "hooks.json"
            target.write_text(json.dumps(_legacy_doc()), encoding="utf-8")

            hooks_mod.reconcile_codex_hooks(target)

            doc = json.loads(target.read_text(encoding="utf-8"))
            stop_hooks = doc["hooks"]["Stop"][0]["hooks"]
            other = next(h for h in stop_hooks if h["managedBy"] == "psc-bro-return")
            self.assertEqual(other["command"], "PSC_RELAY_EVENT=stop /some/other/psc-bro-return.sh")

    def test_no_legacy_path_remains_after_reconcile(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "hooks.json"
            target.write_text(json.dumps(_legacy_doc()), encoding="utf-8")

            hooks_mod.reconcile_codex_hooks(target)

            text = target.read_text(encoding="utf-8")
            self.assertNotIn("psc-relay-hook.sh", text.replace("cortex relay-hook", ""))
            # 更直接：確認舊絕對路徑片段完全消失
            self.assertNotIn("paulshaclaw/scripts/coordinator/psc-relay-hook.sh", text)

    def test_idempotent_second_run_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "hooks.json"
            target.write_text(json.dumps(_legacy_doc()), encoding="utf-8")

            first = hooks_mod.reconcile_codex_hooks(target)
            self.assertTrue(first.changed)
            second = hooks_mod.reconcile_codex_hooks(target)
            self.assertFalse(second.changed)

    def test_missing_hooks_file_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "hooks.json"
            result = hooks_mod.reconcile_codex_hooks(target)
            self.assertFalse(result.changed)
            self.assertFalse(target.exists())

    def test_backup_written_when_migration_happens(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "hooks.json"
            target.write_text(json.dumps(_legacy_doc()), encoding="utf-8")

            hooks_mod.reconcile_codex_hooks(target)

            backups = list(Path(d).glob("hooks.json.bak-*"))
            self.assertEqual(len(backups), 1)
            backup_doc = json.loads(backups[0].read_text(encoding="utf-8"))
            self.assertEqual(
                backup_doc["hooks"]["Stop"][0]["hooks"][1]["command"], LEGACY_STOP_COMMAND
            )

    def test_already_canonical_is_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "hooks.json"
            doc = _legacy_doc()
            doc["hooks"]["Stop"][0]["hooks"][1]["command"] = CANONICAL_STOP_COMMAND
            doc["hooks"]["SessionStart"][0]["hooks"][0]["command"] = CANONICAL_SESSION_START_COMMAND
            target.write_text(json.dumps(doc), encoding="utf-8")

            result = hooks_mod.reconcile_codex_hooks(target)
            self.assertFalse(result.changed)

    def test_default_codex_hooks_path_uses_home(self) -> None:
        home = Path("/tmp/fake-home")
        self.assertEqual(hooks_mod.default_codex_hooks_path(home), home / ".codex" / "hooks.json")


if __name__ == "__main__":
    unittest.main()
