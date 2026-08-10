### Fixed
- **integrator prompt 補結構語意，修復必然的空 `artifact_refs` 驗證失敗**：`build_production_planning_runtime` 的 integrator prompt 過去只列欄位名，未說明 `artifact_refs` 須為非空的 destination path 清單、`artifact_kind` 須對應 question kind 去掉 `missing-` 前綴、artifacts path 集合須恰等於 refs 聯集、每題恰一 resolution——模型在無語意指引下把不確定欄位留空，`validate_primary_integration` 必然拒收（canary v2 gen2 實測）。prompt 補上四項約束並以回歸測試釘住關鍵語句；validator 不動。
