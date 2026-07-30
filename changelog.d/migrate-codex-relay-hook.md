### Fixed
- **Issue #155：install/upgrade 遷移 Codex 全域 relay hook**：新增
  `paulsha_cortex.deploy.hooks.reconcile_codex_hooks()`，於 `cortex install service`
  流程 idempotent 改寫 `$HOME/.codex/hooks.json` 內 `managedBy: psc-coordinator-relay`
  的 legacy 絕對路徑 entry 為 canonical 的 `cortex relay-hook`，修補 Codex Stop hook
  exit 127 的 migration gap；改寫前備份原檔、只動 Cortex 自管 entries、全程 fail-open
  不中斷安裝，systemctl 步驟失敗時仍回報已發生的遷移結果。
