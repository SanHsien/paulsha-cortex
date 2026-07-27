"""#212：CompletionRecord 新增「final 發現 plan 錯而非 candidate 錯」的訊號欄位。

供 #137 度量 plan review 漏檢：plan_review_gate（#212 主體）在 plan 階段判定通過，
但 final 才發現問題其實出在 plan 而非 candidate 實作時，於此記一筆 provenance 訊號。
純 provenance，不影響既有 completion 語意，semantic match 需忽略它（比照 reused_from）。
"""

from __future__ import annotations

import unittest

from paulsha_cortex.coordinator import completion


def _base_payload(**overrides: object) -> dict:
    payload = {
        "schema_version": completion.COMPLETION_SCHEMA_VERSION,
        "slice_id": "plan-review-gate",
        "spec_hash": "1" * 64,
        "plan_hash": "2" * 64,
        "verification_hash": "3" * 64,
        "builder_job_id": "builder-1",
        "reviewer_job_id": None,
        "dispatch_base": "a" * 40,
        "candidate": "b" * 40,
        "target_branch": "main",
        "target_remote": "origin",
        "target_ref": "refs/remotes/origin/main",
        "target_ref_sha": "c" * 40,
        "verification_evidence_path": "evidence/verification.json",
        "verification_evidence_hash": "4" * 64,
        "review_policy": "not-required",
        "docs_class": "trivial",
        "review_evaluation_path": None,
        "review_evaluation_hash": None,
        "completed_at": "2026-07-27T00:00:00+00:00",
    }
    payload.update(overrides)
    return payload


class FinalDefectLocusValidationTests(unittest.TestCase):
    def test_absent_final_defect_locus_still_validates(self) -> None:
        normalized = completion.validate_completion_record(_base_payload())
        self.assertNotIn("final_defect_locus", normalized)

    def test_plan_locus_round_trips(self) -> None:
        normalized = completion.validate_completion_record(
            _base_payload(final_defect_locus="plan")
        )
        self.assertEqual(normalized["final_defect_locus"], "plan")

    def test_candidate_locus_round_trips(self) -> None:
        normalized = completion.validate_completion_record(
            _base_payload(final_defect_locus="candidate")
        )
        self.assertEqual(normalized["final_defect_locus"], "candidate")

    def test_unknown_locus_value_rejected(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(
                _base_payload(final_defect_locus="builder")
            )

    def test_non_string_locus_value_rejected(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(_base_payload(final_defect_locus=1))


class FinalDefectLocusSemanticMatchTests(unittest.TestCase):
    def test_final_defect_locus_excluded_from_semantic_match(self) -> None:
        existing = _base_payload()
        incoming = _base_payload(final_defect_locus="plan")
        self.assertTrue(completion.completion_records_semantically_match(existing, incoming))

    def test_differing_final_defect_locus_still_matches(self) -> None:
        existing = _base_payload(final_defect_locus="plan")
        incoming = _base_payload(final_defect_locus="candidate")
        self.assertTrue(completion.completion_records_semantically_match(existing, incoming))

    def test_real_conflict_still_detected_alongside_final_defect_locus(self) -> None:
        existing = _base_payload(final_defect_locus="plan")
        incoming = _base_payload(final_defect_locus="plan", candidate="d" * 40)
        self.assertFalse(completion.completion_records_semantically_match(existing, incoming))


if __name__ == "__main__":
    unittest.main()
