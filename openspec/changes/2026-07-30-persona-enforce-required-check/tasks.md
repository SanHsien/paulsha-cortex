---
status: accepted
work_item: persona-enforce-required-check
---

# Tasks

- [ ] 1.1 RED：依 `docs/superpowers/plans/persona-enforce-required-check.md` 的 TDD RED 章節新增測試，確認失敗。
- [ ] 1.2 實作至 GREEN，範圍限於 `docs/superpowers/specs/persona-enforce-required-check-spec.md` 的 Requirements。
- [ ] 1.3 `changelog.d/persona-enforce-required-check.md` fragment 與 `CHANGELOG.md [Unreleased]` entry（#135）。
- [ ] 1.4 `python3 -m pytest tests/ -q` 全綠；帶 PR 上下文的 `policy_check` 0 fail；`git diff --check` 乾淨。

## 驗收

歷史回放零誤殺且可重跑；enforcement 為 enforce；違規回非零並可定位；persona-scope 為 required check；豁免不靜音。
