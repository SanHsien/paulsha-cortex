"""#135：persona enforcement shadow → enforce 切換測試。

對應 docs/superpowers/plans/persona-enforce-required-check.md 第 1 節、
docs/superpowers/specs/persona-enforce-required-check-spec.md R1~R4。
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PERSONAS_YAML = REPO_ROOT / "paulsha_cortex" / "persona" / "personas.yaml"


def _valid_manifest(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "from_role": "planner",
        "to_role": "reviewer",
        "phase": "review",
        "gate_status": "passed",
        "slice_id": "persona-enforce-required-check",
        "summary": "enforce switchover coverage",
        "artifact_refs": ["feature/135-persona-enforce-required-check"],
        "created_at": "2026-07-30T00:00:00+08:00",
        "base": "main",
        "head": "feature/135-persona-enforce-required-check",
    }
    payload.update(overrides)
    return payload


def _write_manifest(repo_root: Path, **overrides: object) -> Path:
    from paulsha_cortex.persona import handoff

    path = repo_root / "runtime" / "handoff" / "persona-enforce-required-check.json"
    handoff.write_manifest(path, _valid_manifest(**overrides))
    return path


def _run(repo_root: Path, env: dict[str, str]) -> tuple[int, dict[str, object]]:
    """跑 scope_ci.main 並擷取 stdout 最後一行 JSON verdict。"""
    from paulsha_cortex.persona import scope_ci

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = scope_ci.main(argv=["--repo", str(repo_root)], env=env)
    out = buf.getvalue().strip().splitlines()
    payload = json.loads(out[-1]) if out else {}
    return code, payload


def _patch_diff(case: unittest.TestCase, paths: list[str]) -> None:
    from paulsha_cortex.persona import gate

    original = gate.compute_changed_paths
    gate.compute_changed_paths = lambda base, head, repo=None: list(paths)
    case.addCleanup(setattr, gate, "compute_changed_paths", original)


def _patch_enforcement(case: unittest.TestCase, mode: str) -> None:
    """強制 scope_ci 以指定 enforcement mode 執行，不受真實 personas.yaml 影響。"""
    from paulsha_cortex.persona import scope_ci

    original = scope_ci.load_enforcement
    scope_ci.load_enforcement = lambda *a, **k: mode
    case.addCleanup(setattr, scope_ci, "load_enforcement", original)


class HistoricalReplayTests(unittest.TestCase):
    def test_historical_replay_has_zero_false_positives(self) -> None:
        """R1 / D1：以近期已合併 PR 檔案清單回放 persona scope 判定，零誤殺、可重跑。"""
        from paulsha_cortex.persona import replay

        summary = replay.replay(repo_root=REPO_ROOT, limit=30, ref="main")

        # 回放必須實際掃到東西，避免空回放偽造零誤殺。
        self.assertGreater(summary["prs_scanned"], 0, msg="回放未掃到任何已合併 PR")
        self.assertGreater(summary["files_scanned"], 0, msg="回放未掃到任何檔案異動")
        self.assertEqual(
            summary["false_positives"],
            0,
            msg=(
                "歷史回放出現誤殺，須修正 persona scope 契約本身，"
                f"不得放寬檢查：{json.dumps(summary, ensure_ascii=False, indent=2)}"
            ),
        )

        # 可重跑：同樣輸入應得到同樣結論（結構化、非一次性手算）。
        rerun = replay.replay(repo_root=REPO_ROOT, limit=30, ref="main")
        self.assertEqual(rerun["false_positives"], summary["false_positives"])
        self.assertEqual(rerun["prs_scanned"], summary["prs_scanned"])


class ViolationExitCodeTests(unittest.TestCase):
    def test_violation_returns_nonzero(self) -> None:
        """R2：enforce 模式下偵測到違規時 persona-scope.yml（scope_ci）SHALL 回非零。"""
        _patch_enforcement(self, "enforce")
        # planner write_paths 不含 paulsha_cortex/** → 越界
        _patch_diff(self, ["paulsha_cortex/persona/scope_ci.py"])
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            _write_manifest(repo, from_role="planner")
            code, payload = _run(repo, {"GITHUB_BASE_REF": "main"})
            self.assertNotEqual(code, 0)
            self.assertFalse(payload["ok"])

    def test_in_scope_change_still_exits_zero_in_enforce(self) -> None:
        """對照組：enforce 模式下合規變更仍必須放行，避免誤把 enforce 做成恆擋。"""
        _patch_enforcement(self, "enforce")
        _patch_diff(self, ["docs/superpowers/specs/foo.md"])
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            _write_manifest(repo, from_role="planner")
            code, payload = _run(repo, {"GITHUB_BASE_REF": "main"})
            self.assertEqual(code, 0)
            self.assertTrue(payload["ok"])


class ViolationMessageTests(unittest.TestCase):
    def test_violation_message_locates_persona_paths_and_rule(self) -> None:
        """R2 / D3：違規輸出須含 persona、實際觸及路徑、違反的 scope 規則三者。"""
        _patch_enforcement(self, "enforce")
        _patch_diff(
            self,
            ["paulsha_cortex/persona/scope_ci.py", "docs/superpowers/specs/ok.md"],
        )
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            _write_manifest(repo, from_role="planner")
            code, payload = _run(repo, {"GITHUB_BASE_REF": "main"})
            self.assertNotEqual(code, 0)

            # persona（role）可定位
            self.assertEqual(payload["role"], "planner")

            # 實際觸及路徑可定位
            offending_paths = [v["path"] for v in payload["violations"]]
            self.assertIn("paulsha_cortex/persona/scope_ci.py", offending_paths)
            self.assertNotIn("docs/superpowers/specs/ok.md", offending_paths)

            # 違反的 scope 規則可定位
            for violation in payload["violations"]:
                self.assertIn("rule_id", violation)
                self.assertTrue(violation["rule_id"])
                self.assertIn("reason", violation)
                self.assertTrue(violation["reason"])
                self.assertIn(violation["path"], violation["reason"])


class ExemptionLabelTests(unittest.TestCase):
    def test_exemption_label_allows_merge_but_keeps_output(self) -> None:
        """R4 / D4：套用 policy-exempt:persona-scope 時不阻擋，但仍輸出違規內容。"""
        _patch_enforcement(self, "enforce")
        _patch_diff(self, ["paulsha_cortex/persona/scope_ci.py"])
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            _write_manifest(repo, from_role="planner")

            # 無豁免：擋下
            code_blocked, payload_blocked = _run(repo, {"GITHUB_BASE_REF": "main"})
            self.assertNotEqual(code_blocked, 0)
            self.assertTrue(payload_blocked["violations"])

            # 有豁免：不擋，但違規內容仍在輸出中
            code_exempt, payload_exempt = _run(
                repo,
                {
                    "GITHUB_BASE_REF": "main",
                    "PERSONA_SCOPE_PR_LABELS": "policy-exempt:persona-scope,other-label",
                },
            )
            self.assertEqual(code_exempt, 0)
            self.assertTrue(payload_exempt["exempted"])
            self.assertTrue(payload_exempt["violations"])  # 豁免不靜音
            offending_paths = [v["path"] for v in payload_exempt["violations"]]
            self.assertIn("paulsha_cortex/persona/scope_ci.py", offending_paths)

    def test_unrelated_label_does_not_exempt(self) -> None:
        _patch_enforcement(self, "enforce")
        _patch_diff(self, ["paulsha_cortex/persona/scope_ci.py"])
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            _write_manifest(repo, from_role="planner")
            code, payload = _run(
                repo, {"GITHUB_BASE_REF": "main", "PERSONA_SCOPE_PR_LABELS": "wip"}
            )
            self.assertNotEqual(code, 0)
            self.assertFalse(payload["exempted"])


class EnforcementModeTests(unittest.TestCase):
    def test_enforcement_mode_is_enforce(self) -> None:
        """personas.yaml 的 enforcement SHALL 為 enforce。"""
        from paulsha_cortex.persona.loader import load_enforcement

        self.assertEqual(load_enforcement(), "enforce")

        raw = PERSONAS_YAML.read_text(encoding="utf-8")
        self.assertRegex(raw, r"(?m)^enforcement:\s*enforce\s*$")


if __name__ == "__main__":
    unittest.main()
