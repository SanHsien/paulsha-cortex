---
status: accepted
work_item: per-work-model-chain
---

# per-work-model-chain Todo

## Tasks

- [ ] 將 issue #205、active OpenSpec change `2026-07-30-per-work-model-chain` 與本 Todo 綁定為同一 confirmed Work Item。
- [ ] coordinator 派工 codex（gpt-5.3-codex-spark） 以 TDD 完成 #205：先寫 RED 測試，再實作到 GREEN。
- [ ] ForeignReview（claude（claude-opus-5））review 通過；operator 驗收核可。
- [ ] `changelog.d/per-work-model-chain.md` fragment 已新增且已 commit（R-09 硬性 gate）；`CHANGELOG.md [Unreleased]` 有對應 entry。
- [ ] 帶 PR 上下文執行 `policy_check`（`--pr-title`／`--pr-body`／`--pr-labels`／`--pr-base-ref`／`--pr-head-ref`）確認 fail: 0；全套 pytest 通過。
