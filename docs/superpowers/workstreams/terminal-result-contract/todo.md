---
status: accepted
work_item: terminal-result-contract
---

# terminal-result-contract Todo

## Tasks

- [ ] 將 issue #261、active OpenSpec change `2026-07-30-terminal-result-contract` 與本 Todo 綁定為同一 confirmed Work Item。
- [ ] coordinator 派工 codex（gpt-5.3-codex-spark） 以 TDD 完成 #261：先寫 RED 測試，再實作到 GREEN。
- [ ] ForeignReview（claude（claude-opus-5））review 通過；operator 驗收核可。
- [ ] `changelog.d/terminal-result-contract.md` fragment 已新增且已 commit（R-09 硬性 gate）；`CHANGELOG.md [Unreleased]` 有對應 entry。
- [ ] 帶 PR 上下文執行 `policy_check`（`--pr-title`／`--pr-body`／`--pr-labels`／`--pr-base-ref`／`--pr-head-ref`）確認 fail: 0；全套 pytest 通過。
