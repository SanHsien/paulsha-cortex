"""#222（design #208 H.2）：CompletionRecord 新增 sizing_score/sizing_band/
sizing_declaration_drift 三個可選 provenance 欄位。

比照 #212 final_defect_locus 的模式（見 test_completion_final_defect_locus.py）：
可選欄位＋_normalize_*＋extras 白名單聯集；band 屬 work item 狀態快照，
semantic match 需忽略它（比照 reused_from）。sizing_band 必須與 sizing_score
依 claim.sizing_band() 算出的門檻一致，否則 fail-closed。
"""

from __future__ import annotations

import unittest

from paulsha_cortex.coordinator import claim, completion


def _base_payload(**overrides: object) -> dict:
    payload = {
        "schema_version": completion.COMPLETION_SCHEMA_VERSION,
        "slice_id": "sizing-band-gate",
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


class SizingScoreBandValidationTests(unittest.TestCase):
    def test_absent_sizing_fields_still_validate(self) -> None:
        normalized = completion.validate_completion_record(_base_payload())
        self.assertNotIn("sizing_score", normalized)
        self.assertNotIn("sizing_band", normalized)

    def test_consistent_score_and_band_round_trip(self) -> None:
        normalized = completion.validate_completion_record(
            _base_payload(sizing_score=2, sizing_band="green")
        )
        self.assertEqual(normalized["sizing_score"], 2)
        self.assertEqual(normalized["sizing_band"], "green")

    def test_all_three_bands_accept_their_matching_score_range(self) -> None:
        for total, band in ((0, "green"), (3, "green"), (4, "yellow"), (6, "yellow"), (7, "red"), (10, "red")):
            with self.subTest(total=total, band=band):
                normalized = completion.validate_completion_record(
                    _base_payload(sizing_score=total, sizing_band=band)
                )
                self.assertEqual(normalized["sizing_band"], band)
                self.assertEqual(normalized["sizing_band"], claim.sizing_band(total))

    def test_score_without_band_rejected(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(_base_payload(sizing_score=2))

    def test_band_without_score_rejected(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(_base_payload(sizing_band="green"))

    def test_band_not_matching_score_threshold_rejected(self) -> None:
        # 8 落在 red 區間；宣稱 green 必須 fail-closed。
        with self.assertRaises(ValueError):
            completion.validate_completion_record(
                _base_payload(sizing_score=8, sizing_band="green")
            )

    def test_case_variant_band_string_rejected(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(
                _base_payload(sizing_score=0, sizing_band="Green")
            )

    def test_score_out_of_range_rejected(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(
                _base_payload(sizing_score=11, sizing_band="red")
            )

    def test_non_integer_score_rejected(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(
                _base_payload(sizing_score=2.0, sizing_band="green")
            )


class SizingDeclarationDriftValidationTests(unittest.TestCase):
    def test_absent_drift_still_validates(self) -> None:
        normalized = completion.validate_completion_record(_base_payload())
        self.assertNotIn("sizing_declaration_drift", normalized)

    def test_drift_round_trips(self) -> None:
        normalized = completion.validate_completion_record(
            _base_payload(
                sizing_declaration_drift={"declared_modules": 2, "actual_modules": 5}
            )
        )
        self.assertEqual(
            normalized["sizing_declaration_drift"],
            {"declared_modules": 2, "actual_modules": 5},
        )

    def test_drift_independent_of_sizing_score_band(self) -> None:
        # sizing_declaration_drift 可單獨出現，不強制與 sizing_score/sizing_band 成對。
        normalized = completion.validate_completion_record(
            _base_payload(
                sizing_declaration_drift={"declared_modules": 1, "actual_modules": 1}
            )
        )
        self.assertNotIn("sizing_score", normalized)
        self.assertNotIn("sizing_band", normalized)

    def test_missing_key_rejected(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(
                _base_payload(sizing_declaration_drift={"declared_modules": 1})
            )

    def test_extra_key_rejected(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(
                _base_payload(
                    sizing_declaration_drift={
                        "declared_modules": 1,
                        "actual_modules": 1,
                        "note": "extra",
                    }
                )
            )

    def test_negative_counts_rejected(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(
                _base_payload(
                    sizing_declaration_drift={"declared_modules": -1, "actual_modules": 1}
                )
            )

    def test_non_int_counts_rejected(self) -> None:
        with self.assertRaises(ValueError):
            completion.validate_completion_record(
                _base_payload(
                    sizing_declaration_drift={"declared_modules": "1", "actual_modules": 1}
                )
            )


class SizingFieldsSemanticMatchTests(unittest.TestCase):
    def test_sizing_score_and_band_excluded_from_semantic_match(self) -> None:
        existing = _base_payload()
        incoming = _base_payload(sizing_score=8, sizing_band="red")
        self.assertTrue(completion.completion_records_semantically_match(existing, incoming))

    def test_differing_sizing_score_and_band_still_matches(self) -> None:
        existing = _base_payload(sizing_score=2, sizing_band="green")
        incoming = _base_payload(sizing_score=8, sizing_band="red")
        self.assertTrue(completion.completion_records_semantically_match(existing, incoming))

    def test_sizing_declaration_drift_excluded_from_semantic_match(self) -> None:
        existing = _base_payload()
        incoming = _base_payload(
            sizing_declaration_drift={"declared_modules": 1, "actual_modules": 9}
        )
        self.assertTrue(completion.completion_records_semantically_match(existing, incoming))

    def test_real_conflict_still_detected_alongside_sizing_fields(self) -> None:
        existing = _base_payload(sizing_score=2, sizing_band="green")
        incoming = _base_payload(
            sizing_score=2, sizing_band="green", candidate="d" * 40
        )
        self.assertFalse(completion.completion_records_semantically_match(existing, incoming))


if __name__ == "__main__":
    unittest.main()
