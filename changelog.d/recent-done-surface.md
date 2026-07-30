### Fixed
- **Issue #230／#265：`recent_done` 補投影欄位並加入 recency window**：
  `recent_done_provider()` 除既有 `slice_id`／`gate_status`／`at` 外，多投影 handoff
  manifest 已有的 `gate_reason`／`job_id`／`branch`（缺欄位時為 `null`，不拋錯），讓
  consumer 端的 `needs_human` 條目不再只顯示「待裁決 · 原因未知」（#230）；同時加入
  可設定的 recency window（`RECENT_DONE_WINDOW_SECONDS`，預設 86400 秒，可經
  `--recent-done-window-seconds` 或 `PSC_MANAGER_RECENT_DONE_WINDOW_SECONDS` 覆寫），
  過期 manifest 不再進入 `recent_done`，window 內無資料時回空陣列而不回退撈更舊紀錄
  （#265）。naive `completed_at` 一律視為 UTC，避免本地時區造成新鮮度誤判。
