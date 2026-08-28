---
status: accepted
work_item: planning-claim-recovery
---

# planning-claim-recovery Plan

## Tasks

### 1. TDD RED

- [ ] `tests/test_planning_claim_recovery.py`：
  - `test_environment_failure_is_recoverable`：planning 因 identity 不可用而失敗的 run，恢復動作放行並重跑 planning。
  - `test_content_failure_is_not_recoverable`：planning 因產物缺失／blocking marker 失敗時，恢復動作拒絕並回報實際原因。
  - `test_resume_returns_reason_and_next_actions`：`resume` 遇 `needs_human` 回傳 blocking reason 與合法動作集合，而非只有狀態字串。
  - `test_abandon_allows_reclaim`：`abandon` 後同一 work item 可用相同 authority 組成重新 claim，不被 `persisted-block` 短路。
  - `test_existing_blocked_runs_unaffected`：既有（無釋放標記的）blocked run 行為不變。
  - `test_recovery_requires_expected_run_id`：恢復動作缺少或帶錯 `expected_run_id` 時拒絕。
  - `test_recovery_is_idempotent`：相同恢復請求重送不產生第二個 planning job 或 run。

### 2. 失敗原因分類

- [ ] 在 run 的 planning 失敗記錄中保留可機械判定的原因分類（環境面 vs 內容面）。
- [ ] 恢復動作依該分類決定放行或拒絕，拒絕時回報實際原因。

### 3. 恢復動作

- [ ] 新增 work action，重跑 planning 並更新 run 的 planning 結果，run identity 與 authority 凍結不變。
- [ ] 要求 `expected_run_id`（CAS），不符即拒絕。
- [ ] 記錄觸發者、判定依據、恢復前後 run 狀態。
- [ ] CLI 與 control queue 白名單同步放行新 action。

### 4. resume 結構化回應

- [ ] `_resume_decision` 對 `needs_human` 改回傳帶 reason 與 `next_actions` 的結構化結果。
- [ ] 沿用既有 `slice_status_entry` 的 `next_actions` 推導模式，不另立一套。

### 5. abandon 釋放語意

- [ ] abandon 在 registry 寫入可辨識的釋放標記。
- [ ] claim 路徑檢查釋放標記後允許同識別重新 claim；`persisted-block` 只對未釋放的 blocked 生效。
- [ ] 釋放標記只對新的 abandon 寫入，不回溯改變既有 blocked run。

### 6. 交付要件

- [ ] `changelog.d/planning-claim-recovery.md` fragment（R-09 硬性 gate，須 commit 才進 diff）。
- [ ] `CHANGELOG.md [Unreleased]` 對應 entry。
- [ ] 更新 operator 文件：恢復桿清單與各自適用情境。
- [ ] 帶 PR 上下文執行 policy_check，確認 fail: 0。
- [ ] 全套 pytest 通過。
