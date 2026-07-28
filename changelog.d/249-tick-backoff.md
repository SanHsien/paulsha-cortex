### Fixed

- **Issue #249：daemon tick 失敗不再退化為熱迴圈**：`manager_daemon.run_loop` 的 periodic tick 失敗時同樣推進排程時鐘並採指數退避（`tick_interval * 2^min(連續失敗數, 4)`，上限 16 倍），成功後即重置為正常間隔；連續失敗達門檻（`TICK_CIRCUIT_BREAKER_THRESHOLD = 6`）後熔斷暫停 periodic tick 一小時冷卻期（`TICK_CIRCUIT_BREAKER_COOLDOWN_SECONDS`），request 佇列（含人工 tick request，操作者的救援管道）處理完全不受影響，且人工 tick 成功會自動重置熔斷狀態。`status.json` 的 `daemon` 區塊新增 `consecutive_tick_failures`／`tick_circuit_open`／`last_tick_error`（已去識別化的型別＋原因摘要）觀測欄位。`_log_error` 對同一錯誤簽章的連續重複改為每 50 次輸出一則彙總，不再逐行全文重刷（第一次仍完整輸出）。
