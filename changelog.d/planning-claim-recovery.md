### Fixed
- **Issue #256：planning claim 恢復與放行語意修正**：新增 `recover-planning` work action，要求 `expected_run_id`、`failure_classification`、`failure_reason`，並依環境/內容失敗分類做 fail-closed 決策；`abandon` 透過 `planning_released` 允許同一 work item 重新 claim，不再把新 claim 永久封為 `persisted-block`；`recover-planning` 新增 evidence 落地（`evidence/planning-recovery`）與 CAS 重放邏輯，實作完成後 `resume` 的 `needs_human` 狀態也回報 `next_actions`。
