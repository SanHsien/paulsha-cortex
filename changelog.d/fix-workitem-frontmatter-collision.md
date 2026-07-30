### Fixed
- **Issue #273（實例修正）：openspec change 內 frontmatter `work_item` 不一致**：
  `openspec/changes/fix-systemctl-install-failure/tasks.md` 宣告的 `work_item` 與同目錄
  `proposal.md`／`design.md` 不同，使同一個 openspec source 被兩個 work item 宣告擁有，
  觸發 `correlate_work_sources` 的 confirmed source collision，導致 `hamanpaul/paulsha-cortex`
  的 work item projection 由 43 個降為 0、任何 work item 都無法 claim。本次對齊 frontmatter；
  collision 只影響單一 source 卻讓整個 repo 歸零、以及 refresh 例外被靜默吞掉的根本問題見 #273。
