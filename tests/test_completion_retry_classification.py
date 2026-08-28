"""#215：CompletionRecord 的 retry_classification provenance 欄位。

驗收條件對應：
- 「分類寫入 CompletionRecord，cortex stat 可依分類彙總」——本檔驗證 schema 層
  的可選欄位驗證／正規化／round-trip，比照 #214 reused_from 的 provenance 模式。
"""

from __future__ import annotations

import unittest

from paulsha_cortex.coordinator import completion


def _base_payload(**overrides: object) -> dict:
    payload = {
        "schema_version": completion.COMPLETION_SCHEMA_VERSION,
        "slice_id": "retry-classification",
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
        "verification_evidence_path": "/evidence/verification.json",
        "verification_evidence_hash": "4" * 64,
        "review_policy": "not-required",
        "docs_class": "trivial",
        "review_evaluation_path": None,
        "review_evaluation_hash": None,
        "completed_at": "2026-07-27T00:00:00+00:00",
    }
    payload.update(overrides)
    return payload


class RetryClassificationValidationTests(unittest.TestCase):
    def test_absent_retry_classification_still_validates(self) -> None:
        normalized = completion.validate_completion_record(_base_payload())
        self.assertNotIn("retry_classification", normalized)

    def test_model_repair_round_trips(self) -> None:
        normalized = completion.validate_completion_record(
            _base_payload(retry_classification="model_repair")
        )
        self.assertEqual(normalized["retry_classification"], "model_repair")

    def test_orchestrator_retry_round_trips(self) -> None:
        normalized = completion.validate_completion_record(
            _base_payload(retry_classification="orchestrator_retry")
        )
        self.assertEqual(normalized["retry_classification"], "orchestrator_retry")

    def test_future_wave_values_are_already_accepted_by_schema(self) -> None:
        # #216 補齊 authority_restart/review_handoff_failure/source_owner_repair
        # 的判準，但 enum 值本身在 #215 已定案，schema 現在就必須接受。
        for value in (
            "authority_restart",
            "review_handoff_failure",
            "source_owner_repair",
        ):
            normalized = completion.validate_completion_record(
                _base_payload(retry_classification=value)
            )
            self.assertEqual(normalized["retry_classification"], value)

    def test_rejects_unknown_classification(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(
                _base_payload(retry_classification="not-a-real-classification")
            )

    def test_rejects_non_string_classification(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(
                _base_payload(retry_classification=123)
            )


class RetryClassificationSemanticMatchTests(unittest.TestCase):
    def test_retry_classification_excluded_from_semantic_match(self) -> None:
        existing = _base_payload()
        incoming = _base_payload(retry_classification="model_repair")
        self.assertTrue(completion.completion_records_semantically_match(existing, incoming))

    def test_differing_retry_classification_still_matches(self) -> None:
        existing = _base_payload(retry_classification="model_repair")
        incoming = _base_payload(retry_classification="orchestrator_retry")
        self.assertTrue(completion.completion_records_semantically_match(existing, incoming))

    def test_real_conflict_still_detected_alongside_retry_classification(self) -> None:
        existing = _base_payload(retry_classification="model_repair")
        incoming = _base_payload(
            retry_classification="model_repair",
            verification_hash="9" * 64,
        )
        self.assertFalse(completion.completion_records_semantically_match(existing, incoming))


if __name__ == "__main__":
    unittest.main()
