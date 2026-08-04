### Added
- **批次 W1 planning artifacts（#295／#291、#260、#178、#139）**：為四個 work item
  （`fix-persona-catalog-portability`〔#295 primary＋#291 duplicate 一修多關的 multi-issue
  Work Item〕、`fix-repair-commit-recovery`、`feat-work-gc`、`design-task-type-taxonomy`）
  各新增 `docs/superpowers/specs/<wi>-spec.md`、`-design.md`、`docs/superpowers/plans/<wi>.md`、
  `docs/superpowers/workstreams/<wi>/todo.md` 與 `openspec/changes/2026-08-04-<wi>/`
  （proposal／tasks／spec delta），並登錄 `.cortex/work-items.yaml`，作為 cortex
  work-item lifecycle 的 confirmed authority。本 PR 只提供 planning authority，不含實作。
