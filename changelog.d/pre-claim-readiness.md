### Added

- **Issue #211：新增 pre-claim readiness 檢查與凍結集**：新增 `coordinator/claim_readiness.py`，依成本排序執行六項 pre-claim 檢查（heading/OpenSpec/changelog scope → base SHA → monitor snapshot → GitHub owner → capability → live probe，live probe 最後且帶 TTL 快取），輸出為可序列化的凍結集（frozen SHA/hash 組）而非布林值；失敗分終局（policy scope 契約互斥）與可重試兩類。`work_actions._claim_action` 新增可注入的 `readiness_checker`，任一檢查失敗即在建立 workflow job/worktree/model session 之前擋下。
