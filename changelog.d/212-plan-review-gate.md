### Added

- **Issue #212：新增 plan review gate 三項判定**：`planning.py` 新增 `plan_review_gate()`，依 cost order 跑完整性（每個 acceptance surface 有對應 task）／契約相容性（plan scope 與呼叫端算好的 R-09/R-16/R-19/R-22 相容，明確排除項目與規則衝突時是 hippo #18 第 9 條的 terminal case）／封套相符（plan 宣告的 `invariant_count`／`artifact_classes` 落在 #209 builder 封套內，封套資料缺席時記 `envelope_unavailable` 可觀測 bypass）三項判定，任一不過即 fail closed；`completion.py` 新增 `final_defect_locus` 訊號欄位，記錄 final 才發現問題出在 plan 而非 candidate 的訊號（供 #137 度量 plan review 漏檢），純 provenance 不影響 semantic match。
