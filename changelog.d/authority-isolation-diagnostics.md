### Fixed

- **Issue #206：durable GitHub provider authority invalid 仍復發且缺診斷**：`claim.load_work_authorities()` 改為逐 row 隔離解析——單一 row 的 provider/欄位驗證失敗不再中止整批載入，只把該 row 標記為不可用並繼續解析其餘 row；`load_work_authority(repo=, work_id=)` 因此不再被無關 repo 的壞 provider 誤阻斷，同時對「目標本身就是壞 row」的查詢改拋出帶 reason code 的精準錯誤，維持既有 fail-closed（壞 row 仍不出現在回傳結果中）。新增 `AuthorityValidationError(ValueError)`，攜帶不含機密的 `reason_code`／`repo`／`work_id`／`provider_id`／`field`，並讓 canonical（`provider-authority-*-canonical`）與 legacy（`provider-authority-*-legacy`）schema 的失敗 reason 各自可分辨；#217 的 identity 重複／雙 owner 完整性檢查維持原 raise 行為未動。
