### Added
- **Refs #292：實作 subagent / agent 派工收尾的六項確定性機械驗收檢查**：提供零 model
  session 的確定性收尾檢查 (`paulsha_cortex.mechanical_acceptance` 與 `cortex mechanical-acceptance`)，
  包含 1. 自我宣稱 vs 產出比對、2. 輸出內部一致性、3. 摘要 vs 內文一致性、4. 事實新鮮度 (涵蓋 PR body
  與 commit message 的 closing keyword 雙重檢查)、5. 語言規範、6. 禁止無依據量化。提供 `policy-exempt:*`
  白名單豁免與全套正負向測試。
