### Added
- **open-issue 批次 workstream todo 錨點**：為 14 個 work item 新增 `docs/superpowers/workstreams/<work-id>/todo.md`（frontmatter `status: accepted` + `work_item`），並在 `.cortex/work-items.yaml` 補上對應 `path` 連結。lifecycle reducer 需要 active todo 來源才會把 work item 推進 `todo` 態並開放 `start`——issue-only 連結停在 `topic` 不可 claim。各 todo 的任務清單取自對應 issue 2026-08-10 獨立複驗 comment 的修復標的，同時作為 ship gate 的勾選要件。
