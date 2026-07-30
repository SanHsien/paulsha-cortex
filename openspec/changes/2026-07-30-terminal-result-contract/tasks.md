---
status: accepted
work_item: terminal-result-contract
---

# Tasks

- [ ] 1.1 RED：依 `docs/superpowers/plans/terminal-result-contract.md` 的 TDD RED 章節新增測試，確認失敗。
- [ ] 1.2 實作至 GREEN，範圍限於 `docs/superpowers/specs/terminal-result-contract-spec.md` 的 Requirements。
- [ ] 1.3 `changelog.d/terminal-result-contract.md` fragment 與 `CHANGELOG.md [Unreleased]` entry（#261）。
- [ ] 1.4 `python3 -m pytest tests/ -q` 全綠；帶 PR 上下文的 `policy_check` 0 fail；`git diff --check` 乾淨。

## 驗收

任一確定性 gate 失敗而 terminal 自稱 `passed` 時 fail closed 並保留矛盾原因；三類 card 皆可合法輸出四種形狀；schema retry 有上限且可觀測；parse 失敗不遺失診斷也不授予 authority。
