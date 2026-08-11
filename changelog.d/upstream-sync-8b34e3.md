### Added
- 追補 upstream `#450` 的 `retire-delivered` orphan-run 退休流程與限流時的窄化 last-known-good authority；同步把 `#449` 完成狀態及 open release PR `#451` 的延後條件寫入 upstream ledger。

### Fixed
- 強化 `retire-delivered`：GitHub PR lifecycle 的 merged timestamp／state 組合必須一致，且首次寫入與重入共用 evidence 大小上限，避免 malformed open PR 被誤退休或成功後無法冪等重入。
