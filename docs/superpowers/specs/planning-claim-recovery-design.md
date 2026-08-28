---
status: accepted
work_item: planning-claim-recovery
---

# planning-claim-recovery Design

## Decisions

### D1 恢復以「重跑 planning」為單位，不是「重建 run」

新增的恢復動作重新執行 planning 階段並更新 run 的 planning 結果，run identity（run id、claim key）維持不變。

理由：重建 run 會丟掉既有的 authority 凍結與稽核鏈，且會撞上 claim key 唯一性。既然失敗發生在 planning 執行本身、而 authority 與 work item 識別都沒變，重跑的最小單位就是 planning。

### D2 可恢復性由失敗原因分類決定，不由 operator 宣告

恢復動作先讀 run 記錄的 planning 失敗原因，判定其屬於環境面（identity 不可用、probe 失敗、runtime 缺失）才放行；內容面失敗（產物缺失、blocking marker）拒絕並回報實際原因。

理由：如果讓 operator 自行宣告「這是環境問題」，這個動作就會變成繞過 planning 完整性的萬用後門。分類判定放在系統側，才能同時滿足「可恢復」與「fail-closed」。

### D3 resume 回應改為攜帶 blocking reason 與合法動作集合

`_resume_decision` 對 `needs_human` 的回傳從單一狀態字串，改為帶 reason 與 `next_actions` 的結構化結果。

理由：這與 #230 在 status surface 上做的事同源——「狀態」本身不足以指導行動，要帶出為什麼與下一步。既有的 `slice_status_entry` 已經有 `next_actions` 推導的先例，可沿用同一模式。

### D4 abandon 寫入明確的釋放標記，而非僅標 blocked

abandon 在 registry 留下可辨識的釋放標記，claim 路徑檢查該標記後允許同識別重新 claim，`persisted-block` 只對未釋放的 blocked 狀態生效。

理由：目前 `abandon → blocked → persisted-block` 讓 abandon 實質等於「封死」，與其名稱和 operator 預期相反。分離「被阻擋」與「已釋放」兩種 blocked 語意，是最小且語意正確的修法；claim key 的唯一性設計本身不需要改動。

### D5 恢復請求以既有 CAS 模式取得冪等性

恢復動作要求帶 `expected_run_id`（比照 `resume --expected-run-id` 與 `retry-build` 的 `expected_candidate`），不符即拒絕。

理由：repo 既有的恢復桿都用這個模式，沿用可讓 operator 的心智模型一致，也自然得到「重送不會產生第二個 job」的性質。

## 風險與緩解

- **恢復路徑被誤用來繞過內容面失敗**：分類判定在系統側，且拒絕時回報實際原因；恢復動作全程留稽核紀錄，事後可查。
- **abandon 語意變更影響既有 blocked run**：釋放標記只對新的 abandon 寫入，既有 blocked run 行為不變，避免回溯性改變歷史狀態。
- **重跑 planning 期間 run 狀態不一致**：沿用 manager 單一 writer 與 CAS 前提，恢復動作與其他 workflow mutation 互斥。
