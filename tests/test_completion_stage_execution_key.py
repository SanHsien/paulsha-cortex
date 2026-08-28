"""#214：CompletionRecord 的 reused-from provenance 欄位（stage 級 execution key reuse）。

驗收條件對應：
- 「CompletionRecord 記錄 reused-from run/job/evidence hash」
- reused_from 只是 provenance，不應讓良性 reuse 被 semantic match 誤判為衝突。
"""

from __future__ import annotations

import unittest

from paulsha_cortex.coordinator import completion


def _base_payload(**overrides: object) -> dict:
    payload = {
        "schema_version": completion.COMPLETION_SCHEMA_VERSION,
        "slice_id": "stage-execution-key",
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


def _reused_from(**overrides: object) -> dict:
    reused_from = {
        "run_id": "run-1",
        "job_id": "job-1",
        "evidence_hash": "5" * 64,
    }
    reused_from.update(overrides)
    return reused_from


class ReusedFromValidationTests(unittest.TestCase):
    def test_absent_reused_from_still_validates(self) -> None:
        normalized = completion.validate_completion_record(_base_payload())
        self.assertNotIn("reused_from", normalized)

    def test_reused_from_round_trips_normalized_and_lowercases_hash(self) -> None:
        payload = _base_payload(reused_from=_reused_from(evidence_hash=("5" * 64).upper()))
        normalized = completion.validate_completion_record(payload)
        self.assertEqual(
            normalized["reused_from"],
            {"run_id": "run-1", "job_id": "job-1", "evidence_hash": "5" * 64},
        )

    def test_reused_from_rejects_missing_field(self) -> None:
        broken = _reused_from()
        del broken["job_id"]
        with self.assertRaises(ValueError):
            completion.validate_completion_record(_base_payload(reused_from=broken))

    def test_reused_from_rejects_extra_field(self) -> None:
        broken = _reused_from()
        broken["extra"] = "nope"
        with self.assertRaises(ValueError):
            completion.validate_completion_record(_base_payload(reused_from=broken))

    def test_reused_from_rejects_non_hex_evidence_hash(self) -> None:
        broken = _reused_from(evidence_hash="z" * 64)
        with self.assertRaises(ValueError):
            completion.validate_completion_record(_base_payload(reused_from=broken))

    def test_reused_from_rejects_empty_run_id(self) -> None:
        broken = _reused_from(run_id="")
        with self.assertRaises(ValueError):
            completion.validate_completion_record(_base_payload(reused_from=broken))


class ReusedFromSemanticMatchTests(unittest.TestCase):
    def test_reused_from_excluded_from_semantic_match(self) -> None:
        existing = _base_payload()
        incoming = _base_payload(reused_from=_reused_from())
        self.assertTrue(completion.completion_records_semantically_match(existing, incoming))

    def test_differing_reused_from_still_matches(self) -> None:
        existing = _base_payload(reused_from=_reused_from(job_id="job-1"))
        incoming = _base_payload(reused_from=_reused_from(job_id="job-2", run_id="run-2"))
        self.assertTrue(completion.completion_records_semantically_match(existing, incoming))

    def test_real_conflict_still_detected_alongside_reused_from(self) -> None:
        existing = _base_payload(reused_from=_reused_from())
        incoming = _base_payload(
            reused_from=_reused_from(),
            verification_hash="9" * 64,
        )
        self.assertFalse(completion.completion_records_semantically_match(existing, incoming))


if __name__ == "__main__":
    unittest.main()
