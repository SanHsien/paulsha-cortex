---
status: accepted
work_item: terminal-result-contract
---

# terminal-result-contract Plan

## Tasks

### 1. TDD RED

- [x] `tests/test_terminal_result_contract.py`：
  - `test_envelope_supports_all_terminal_states`：canonical envelope 可合法表達 `passed`／`failed`／`needs_human`，且帶 `schema_version`。
  - `test_passed_without_gate_evidence_is_rejected`：terminal 宣稱 `passed` 但無可重驗 gate evidence 時 fail closed。
  - `test_passed_contradicting_failed_gate_is_rejected`：gate command 已失敗而 terminal 自稱 `passed` 時 fail closed，並保留矛盾原因（含 gate 名稱與實際結果）。
  - `test_schema_mismatch_normalizes_known_wrapper_once`：已知 wrapper 外層鍵只 normalize 一次即成功，且不重派模型。
  - `test_unknown_wrapper_shape_terminates_with_actionable_error`：未知形狀不被寬鬆解析吞掉，終止為可操作錯誤。
  - `test_schema_retry_has_bounded_counter`：同一確定性 mismatch 的 retry 次數有上限，超過即停止並記錄計數。
  - `test_parse_failure_keeps_diagnostics_without_authority`：terminal parse 失敗時保留 observed HEAD／job id／reason，且未授予 candidate authority。

### 2. Canonical envelope

- [x] 定義帶 `schema_version` 的 result envelope 與其序列化／反序列化，完整涵蓋三種終局狀態與結構化 diagnostics。
- [x] 舊形狀 payload 走相容讀取路徑並記可觀測的 legacy 標記，不即刻失效。
- [x] build／verify／review 三類 card 的輸出契約對齊同一 envelope。

### 3. Gate evidence cross-check

- [x] harvest 在採信 `passed` 前重讀並驗證 gate evidence（讀檔＋比 hash，不重跑昂貴 gate）。
- [x] 確定性 cross-check 排在狀態採信之前；偵測到矛盾即 fail closed 並保留具體原因。
- [x] 模型文字、exit code 為 0、無明確錯誤三者皆不構成成功授權。

### 4. StructuredOutput normalization 與 retry 上限

- [x] wrapper normalization 採明確白名單，對同一確定性 mismatch 只嘗試一次。
- [x] 保留 machine-readable validation errors；未知形狀終止為可操作錯誤，不回派模型。
- [x] retry 計數器與上限落地，超限即停止。

### 5. 可觀測性

- [x] status／inspect 顯示 schema retry 計數、最後一次 validation path 與 reason。
  - 目前曝光點為 `manager.resume_workflow_run` 回傳的 `schema_retry_count`／
    `schema_retry_limit`／`last_validation_path`／`last_validation_reason`，以及持久化
    於 `WorkflowRun.attempts["schema-mismatch:<card>"]` 的計數；`porcelain inspect`
    的 work-item 摘要尚未把這組欄位獨立列出。
- [x] parse 失敗的唯讀診斷欄位與 authority 欄位分離，兩者不共用。

### 6. 交付要件

- [x] `changelog.d/terminal-result-contract.md` fragment（R-09 硬性 gate，須 commit 才進 diff）。
- [x] `CHANGELOG.md [Unreleased]` 對應 entry。
- [x] 更新 prompt contract 與相關 docs（terminal schema 與狀態語意）。
- [x] 帶 PR 上下文執行 policy_check（`--pr-title`／`--pr-body`／`--pr-labels`／`--pr-base-ref`／`--pr-head-ref`），確認 fail: 0。
- [x] 全套 pytest 通過。
