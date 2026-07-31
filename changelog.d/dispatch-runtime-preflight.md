### Added
- **Issue #262：dispatch 前驗證 runtime capability 與 provider snapshot 新鮮度**：新增
  `coordinator/runtime_preflight.py`，在建立 worktree／sandbox／job row／model session
  之前，於「即將實際被使用的 executor 環境」執行低成本 preflight。card 契約新增
  `runtime_capabilities` 資料宣告（`module:` / `executable:` / `bridge:` / `provider:`），
  preflight 是通用執行器，新增 card 不需改實作；非法宣告在 deck 載入時 fail-closed。
  module 檢查透過 executor 的 interpreter 以子行程 import、executable 只查 executor
  PATH，皆不使用 manager 這側的 import 或 host PATH——`SubprocessLauncher` 新增
  `executor_environment()`，沿用與 `launch()` 相同的 `_git_scope_env()`／
  `_review_scope_env()`，確保 preflight 與正式 job 的 interpreter／PATH／HOME／sandbox
  policy 一致。provider 健康改採「快照 + TTL + 有界 probe」三層，snapshot 帶
  `observed_at`／TTL／source／reason；超過 TTL 的 degraded 判斷不再被當成當前事實
  （這正是 2026-07-30 dogfood 中三個 work item 因過時 `github rate limit exceeded`
  診斷而無法 claim 的成因）。`capability missing`／`provider unavailable`／
  `stale snapshot`／`probe inconclusive` 四種結果各自獨立表達、不折疊成布林，前兩者
  才是 hard block。live probe 以 provider identity 為鍵共用 TTL 快取與 rate-limit 額度
  （沿用 `claim_readiness` 的 `LiveProbeCache` 模式），同批次同 provider 不重複探測。
  preflight 失敗時優先在既有 identity 順序與 independence domain 規則內 re-route，
  無合法替代才進入帶具體 reason 的 `needs_human`，全程 model invocation 維持 0；
  `cortex inspect status` 顯示缺少的 capability、使用中的 executor environment 與
  snapshot 新鮮度。
