---
status: accepted
work_item: per-work-model-chain
---

# per-work-model-chain Plan

## Tasks

### 1. TDD RED

- [ ] `tests/test_per_work_model_chain.py`：
  - `test_override_applies_to_target_run_only`：為某 run 指定模型鏈後，其他 active run 尚未派出的 card 選擇結果不變。
  - `test_override_frozen_at_claim`：覆寫值於 claim 時凍結，之後變更共享 registry 不影響該 run。
  - `test_resume_and_retry_use_frozen_chain`：resume／retry-build／retry-verify／retry-review 沿用凍結值，不重新依共享 registry 選擇。
  - `test_partial_override_falls_back_per_segment`：只覆寫 builder 時，planner／reviewer 回退共享 registry。
  - `test_override_violating_capability_fails_closed`：指定不具該 capability 的 identity 時拒絕並回報原因。
  - `test_override_violating_independence_domain_fails_closed`：builder 與 reviewer 同 domain 時拒絕。
  - `test_unknown_identity_lists_available_candidates`：指定不存在的 model 時，錯誤訊息列出該 capability 下可用 identity。
  - `test_evidence_records_resolution_and_source`：evidence 記錄三段實際 executor／model 與來源標記。

### 2. Run schema 與凍結

- [ ] WorkflowRun 增加 run-scoped 模型鏈覆寫欄位（planner／builder／reviewer 各自 executor 與 model）。
- [ ] 欄位比照既有 provenance-only 欄位處理，排除於 semantic match 之外。
- [ ] claim（或首次 dispatch）時凍結覆寫值。

### 3. 選擇路徑接線

- [ ] `_select_workflow_identity` 在依共享 registry 選擇前，先讀 run 的凍結覆寫。
- [ ] 三段各自獨立；未指定者回退共享 registry。
- [ ] 覆寫仍須通過 capability 與 independence domain 檢查，違反即 fail closed，不靜默退回預設。

### 4. CLI 與 control queue

- [ ] `cortex work` 相關動作新增模型鏈覆寫參數。
- [ ] control queue 白名單同步放行新參數。
- [ ] 提供明確的再次覆寫路徑（operator 顯式操作）。

### 5. 稽核

- [ ] durable evidence 記錄三段解析結果與來源標記（run-scoped override / shared registry）。

### 6. 交付要件

- [ ] `changelog.d/per-work-model-chain.md` fragment（R-09 硬性 gate，須 commit 才進 diff）。
- [ ] `CHANGELOG.md [Unreleased]` 對應 entry。
- [ ] 更新 CLI help 與 docs（R-16 CLI help 同步）。
- [ ] 帶 PR 上下文執行 policy_check，確認 fail: 0。
- [ ] 全套 pytest 通過。
