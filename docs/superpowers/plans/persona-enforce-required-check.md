---
status: accepted
work_item: persona-enforce-required-check
---

# persona-enforce-required-check Plan

## Tasks

### 1. TDD RED

- [ ] `tests/test_persona_scope_enforcement.py`：
  - `test_historical_replay_has_zero_false_positives`：以歷史變更集回放 persona scope 判定，零誤殺。
  - `test_violation_returns_nonzero`：違規變更集使檢查回非零。
  - `test_violation_message_locates_persona_paths_and_rule`：違規輸出含 persona、觸及路徑、違反的 scope 規則。
  - `test_exemption_label_allows_merge_but_keeps_output`：套用 `policy-exempt:persona-scope` 時不阻擋，但仍輸出違規內容。
  - `test_enforcement_mode_is_enforce`：`personas.yaml` 的 enforcement 為 `enforce`。

### 2. 歷史回放

- [ ] 實作可重跑的歷史變更集回放（近期已合併 PR 的檔案清單 → persona scope 判定）。
- [ ] 回放結果納入測試，日後修改 scope 定義即可看出影響。
- [ ] 若回放發現誤殺，修正契約／scope 定義本身；不得以放寬檢查或擴大豁免達成通過。

### 3. Enforcement 切換

- [ ] `personas.yaml` enforcement 由 `shadow` 切為 `enforce`。
- [ ] `persona-scope.yml` 違規時回非零，並輸出可定位訊息（persona／路徑／規則）。

### 4. Required check

- [ ] 將 `persona-scope` 設為 main 的 required status check。
- [ ] 記錄設定步驟於 docs，使此變更可被重現與稽核。

### 5. 豁免機制

- [ ] `policy-exempt:persona-scope` label 生效：不阻擋合併。
- [ ] 豁免時仍輸出違規內容並記錄理由，不靜音。

### 6. 交付要件

- [ ] `changelog.d/persona-enforce-required-check.md` fragment（R-09 硬性 gate，須 commit 才進 diff）。
- [ ] `CHANGELOG.md [Unreleased]` 對應 entry。
- [ ] 更新 docs：enforcement 模式、違規訊息格式、豁免用法與稽核方式。
- [ ] 帶 PR 上下文執行 policy_check，確認 fail: 0。
- [ ] 全套 pytest 通過。
