---
status: accepted
work_item: dispatch-runtime-preflight
---

# dispatch-runtime-preflight Plan

## Tasks

### 1. TDD RED

- [ ] `tests/test_dispatch_runtime_preflight.py`：
  - `test_missing_module_blocks_dispatch_with_zero_model_calls`：executor 環境缺 `pytest` 時 dispatch 前攔截，model invocation count 為 0。
  - `test_missing_executable_blocks_dispatch`：缺 `socat` 時同樣在 dispatch 前攔截。
  - `test_preflight_uses_executor_environment_not_host`：host 有而 executor 環境沒有的 module，preflight 必須判為缺失（不得因 host 有就通過）。
  - `test_stale_degraded_snapshot_is_not_hard_block`：超過 TTL 的 degraded 快照不被當成當前事實。
  - `test_four_outcomes_are_distinguishable`：capability missing／provider unavailable／stale snapshot／probe inconclusive 四種結果可機械區分。
  - `test_reroute_when_alternative_identity_available`：有合法替代 identity 時自動 re-route，仍滿足 capability 與 independence domain 規則。
  - `test_needs_human_carries_specific_reason`：無替代時進入 needs_human 且帶具體 reason。
  - `test_live_probe_respects_budget`：live probe 有 timeout／快取／rate-limit 預算，同批次同 provider 不重複探測。

### 2. Capability 宣告

- [ ] card／persona contract 增加 capability 宣告欄位（interpreter module、executable、bridge、provider）。
- [ ] 宣告為資料驅動，新增 card 不需修改 preflight 實作。

### 3. Preflight 執行

- [ ] 在與正式 job 相同的 executor environment（interpreter、PATH、HOME／sandbox policy、provider identity）中執行低成本探測。
- [ ] 失敗時不建立 model session。
- [ ] 有替代 identity 時 re-route，否則回傳帶具體 reason 的 needs_human。

### 4. Provider snapshot 新鮮度

- [ ] snapshot 增加 `observed_at`／TTL／source／reason。
- [ ] 逾期時對必要 provider 執行有界 live probe，結果回寫快照。
- [ ] 四種結果各自獨立表達，不折疊成布林。

### 5. 成本控制

- [ ] live probe 的 timeout／cache／rate-limit 預算以 provider identity 為鍵，與 preflight 結果快取共用。
- [ ] 沿用既有 `claim_readiness` live probe TTL 快取模式，不另立一套。

### 6. 可觀測性

- [ ] status／inspect 顯示缺少的 capability、使用中的 executor environment、snapshot 新鮮度。

### 7. 交付要件

- [ ] `changelog.d/dispatch-runtime-preflight.md` fragment（R-09 硬性 gate，須 commit 才進 diff）。
- [ ] `CHANGELOG.md [Unreleased]` 對應 entry。
- [ ] 更新 docs：capability 宣告格式與 preflight 行為。
- [ ] 帶 PR 上下文執行 policy_check，確認 fail: 0。
- [ ] 全套 pytest 通過。
