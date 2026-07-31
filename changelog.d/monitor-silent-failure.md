### Fixed
- **Issue #273：修復 Monitor refresh 靜默失敗、同 Repo 多 Checkout 衝突與 Source Collision 歸零缺陷**：
  - 缺陷一：`ProjectMonitorService._refresh_work_model` 不再靜默吞掉 `ValueError` / `OSError` 例外，加入 log 紀錄並於 store / status / snapshot 記錄 `last_refresh_error` 與連續失敗計數；`cortex work show` / `work start` 在 snapshot 停更或 refresh 失敗時直接回報真正原因。
  - 缺陷二：`WorkModelRefresher` 掃描專案時依 git 身分去重同 repo 的多個 checkout，優先選擇 canonical checkout 避免 duplicate work item ID 錯誤，並在 status diagnostics 中明確標示碰撞目錄。
  - 缺陷三：`correlate_work_sources` 與 `project_work_items` 發生 source collision 時，將影響限縮於相關 Work Item 並標記 `degraded` 診斷，不再導致整個 repo 的 Work Item projection 歸零。
