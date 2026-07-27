### Added

- **Issue #213：凍結點移至 plan review 通過之後**：`claim.py` 新增 `claim_identity_digest()`（不含 `mapped_openspec`／`mapped_todo_paths`／`source_revisions` 的穩定 identity）與 `ClaimCandidate.active_plan_review_passed`／`active_claim_identity_digest`；`_existing()` 在 `active_plan_review_passed=False`（plan review 尚未通過）時改用穩定 identity 比對，plan 修訂造成的產物欄位飄移不再被誤判為 authority 變更、不再觸發 supersede（hippo #18 第 3、7 條 v3→v4→… 世代增長 regression）。`planning.py` 新增 `plan_review_freezes_authority()`，把 `plan_review_gate()`（#212）的判定結果對應到「是否可以 freeze」，供呼叫端串接。
