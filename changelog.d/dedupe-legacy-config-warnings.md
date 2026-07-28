### Fixed
- **Issue #254：legacy monitor config 警告去重**：避免 `PAULSHACLAW_CONFIG` 與 `paulshaclaw.yaml`
  在同一 process 重複發出警告；各 legacy 路徑維持逐字一致文案與既有解析順序。
