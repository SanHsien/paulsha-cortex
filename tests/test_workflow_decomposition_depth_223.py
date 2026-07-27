"""#223（design #208 H.3）：WorkflowRun 新增 decomposition_depth 快照欄位，
以及 WORKFLOW_FACETS 新增 needs_decomposition。

比照 #222 sizing_score/sizing_band 的欄位模式：預設值、型別/範圍檢查、
to_dict()/from_dict() 往返，以及舊資料（無此欄位）向後相容。
"""

from __future__ import annotations

import unittest

from paulsha_cortex.coordinator.workflow import (
    WORKFLOW_FACETS,
    WorkflowRun,
    WorkflowStep,
)


def _step() -> WorkflowStep:
    return WorkflowStep(
        phase="plan",
        persona="planner",
        card="writing-plans",
        executor="agy",
        model="gemini-3.1-pro-high",
        domain="google",
        inputs=(),
        outputs=(),
        gate_result="pending",
    )


def _run(**overrides: object) -> WorkflowRun:
    fields: dict[str, object] = {
        "run_id": "workflow-decomposition-depth",
        "work_id": "decomposition-depth-work",
        "repo": "hamanpaul/paulsha-cortex",
        "claim_key": "claim:v1:" + "a" * 64,
        "source_revision": "rev-a",
        "workspace_root": "/tmp/paulsha-cortex",
        "combo": "feature-oneshot",
        "current_phase": "plan",
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


class WorkflowFacetsTests(unittest.TestCase):
    def test_needs_decomposition_is_a_registered_facet(self) -> None:
        self.assertIn("needs_decomposition", WORKFLOW_FACETS)

    def test_needs_decomposition_facet_round_trips(self) -> None:
        run = _run(facets=("needs_decomposition",))
        self.assertEqual(run.facets, ("needs_decomposition",))
        restored = WorkflowRun.from_dict(run.to_dict())
        self.assertEqual(restored.facets, ("needs_decomposition",))


class WorkflowRunDecompositionDepthTests(unittest.TestCase):
    def test_defaults_to_zero(self) -> None:
        run = _run()
        self.assertEqual(run.decomposition_depth, 0)

    def test_valid_depth_round_trips_through_to_dict_from_dict(self) -> None:
        run = _run(decomposition_depth=1)
        self.assertEqual(run.decomposition_depth, 1)
        payload = run.to_dict()
        self.assertEqual(payload["decomposition_depth"], 1)
        restored = WorkflowRun.from_dict(payload)
        self.assertEqual(restored.decomposition_depth, 1)

    def test_from_dict_without_field_defaults_to_zero(self) -> None:
        payload = _run().to_dict()
        payload.pop("decomposition_depth")
        restored = WorkflowRun.from_dict(payload)
        self.assertEqual(restored.decomposition_depth, 0)

    def test_depth_above_limit_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _run(decomposition_depth=3)

    def test_negative_depth_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _run(decomposition_depth=-1)

    def test_non_int_depth_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _run(decomposition_depth=True)
        with self.assertRaises(ValueError):
            _run(decomposition_depth="2")


if __name__ == "__main__":
    unittest.main()
