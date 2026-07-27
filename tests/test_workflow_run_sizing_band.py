"""#222（design #208 H.2）：WorkflowRun 新增 sizing_score／sizing_band 快照欄位。

比照既有 pr_candidate/merge_revision 的 optional trailer 欄位模式：預設 None，
成對出現（有一個就兩個都要），band 字串沿用 deck.schema.BAND_LEVELS。
"""

from __future__ import annotations

import unittest

from paulsha_cortex.coordinator.workflow import WorkflowRun, WorkflowStep


def _step() -> WorkflowStep:
    return WorkflowStep(
        phase="build",
        persona="builder",
        card="test-driven-development",
        executor="agy",
        model="gemini-3.1-pro-high",
        domain="google",
        inputs=(),
        outputs=(),
        gate_result="pending",
    )


def _run(**overrides: object) -> WorkflowRun:
    fields: dict[str, object] = {
        "run_id": "workflow-sizing-band",
        "work_id": "sizing-band-work",
        "repo": "hamanpaul/paulsha-cortex",
        "claim_key": "claim:v1:" + "a" * 64,
        "source_revision": "rev-a",
        "workspace_root": "/tmp/paulsha-cortex",
        "combo": "feature-oneshot",
        "current_phase": "build",
        "steps": (_step(),),
        "issue_refs": (),
        "openspec_refs": (),
        "pr_refs": (),
        "attempts": {},
        "evidence_refs": (),
        "gate_refs": (),
        "brainstorm_required": False,
        "primary_domain": None,
        "candidate_head": None,
        "verified_head": None,
        "facets": (),
        "gate_status": "pending",
        "created_at": "2026-07-27T00:00:00+00:00",
        "updated_at": "2026-07-27T00:00:00+00:00",
    }
    fields.update(overrides)
    return WorkflowRun(**fields)


class WorkflowRunSizingBandTests(unittest.TestCase):
    def test_defaults_to_none(self) -> None:
        run = _run()
        self.assertIsNone(run.sizing_score)
        self.assertIsNone(run.sizing_band)

    def test_valid_pair_round_trips_through_to_dict_from_dict(self) -> None:
        run = _run(sizing_score=8, sizing_band="red")
        self.assertEqual(run.sizing_score, 8)
        self.assertEqual(run.sizing_band, "red")
        payload = run.to_dict()
        self.assertEqual(payload["sizing_score"], 8)
        self.assertEqual(payload["sizing_band"], "red")
        restored = WorkflowRun.from_dict(payload)
        self.assertEqual(restored.sizing_score, 8)
        self.assertEqual(restored.sizing_band, "red")

    def test_from_dict_without_sizing_fields_defaults_to_none(self) -> None:
        payload = _run().to_dict()
        payload.pop("sizing_score")
        payload.pop("sizing_band")
        restored = WorkflowRun.from_dict(payload)
        self.assertIsNone(restored.sizing_score)
        self.assertIsNone(restored.sizing_band)

    def test_score_without_band_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _run(sizing_score=2)

    def test_band_without_score_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _run(sizing_band="green")

    def test_score_out_of_range_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _run(sizing_score=11, sizing_band="red")
        with self.assertRaises(ValueError):
            _run(sizing_score=-1, sizing_band="green")

    def test_unknown_band_string_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _run(sizing_score=1, sizing_band="Green")  # 大小寫變體不合法
        with self.assertRaises(ValueError):
            _run(sizing_score=1, sizing_band="amber")


if __name__ == "__main__":
    unittest.main()
