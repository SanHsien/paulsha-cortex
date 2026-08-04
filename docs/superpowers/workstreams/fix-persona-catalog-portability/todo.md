---
status: accepted
work_item: fix-persona-catalog-portability
---

# fix-persona-catalog-portability Todo

## Tasks

- [ ] 將 issue #295（primary）與 #291（duplicate）、active OpenSpec change `2026-08-04-fix-persona-catalog-portability` 與本 Todo 綁定為同一 confirmed Work Item（multi-issue）；delivery PR body closing keywords 同時涵蓋 `Closes #295` 與 `Closes #291`。
- [ ] coordinator 派工 copilot（gpt-5.4）以 TDD 完成：先寫 RED 測試（`docs/superpowers/plans/fix-persona-catalog-portability.md` Section 1），再實作到 GREEN。
- [ ] ForeignReview（claude/sonnet）review 通過；operator 驗收核可。
- [ ] `changelog.d/fix-persona-catalog-portability.md` fragment 已新增且已 commit（R-09 硬性 gate）；`CHANGELOG.md [Unreleased]` 有對應 entry。
- [ ] 帶 PR 上下文執行 `policy_check`（`--pr-title`／`--pr-body`／`--pr-labels`／`--pr-base-ref`／`--pr-head-ref`）確認 fail: 0；全套 pytest 通過。
