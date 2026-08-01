### Added
- **Refs #292：實作 subagent / agent 派工收尾的六項確定性機械驗收檢查**：提供零 model
  session 的確定性收尾檢查 (`paulsha_cortex.mechanical_acceptance` 與 `cortex mechanical-acceptance`)，
  包含 1. 自我宣稱 vs 產出比對、2. 輸出內部一致性、3. 摘要 vs 內文一致性、4. 事實新鮮度 (涵蓋 PR body
  與 commit message 的 closing keyword 雙重檢查)、5. 語言規範、6. 禁止無依據量化。

### Changed
- **Refs #292：CLI 自動蒐集 context、SKIPPED 狀態與 exit code 語意**：
  - 新增 `--pr <N>` 參數，自動透過 `gh` CLI 抓取 PR body/labels/commits 與被引用的 Issue 狀態。
  - 新增 `--unresolved-issues` 與 `--repo-root` 參數。
  - 缺少判定所需的必要 context 時，狀態明確標示為 `SKIPPED` 並說明缺少的 context，不再盲目回報 `PASS`。
  - exit code 語意明確：全 PASS = 0；有 FAIL = 1；有 SKIPPED 但無 FAIL = 2。
