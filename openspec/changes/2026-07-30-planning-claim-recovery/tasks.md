---
status: accepted
work_item: planning-claim-recovery
---

# Tasks

- [ ] 1.1 RED：依 `docs/superpowers/plans/planning-claim-recovery.md` 的 TDD RED 章節新增測試，確認失敗。
- [ ] 1.2 實作至 GREEN，範圍限於 `docs/superpowers/specs/planning-claim-recovery-spec.md` 的 Requirements。
- [ ] 1.3 `changelog.d/planning-claim-recovery.md` fragment 與 `CHANGELOG.md [Unreleased]` entry（#256）。
- [ ] 1.4 `python3 -m pytest tests/ -q` 全綠；帶 PR 上下文的 `policy_check` 0 fail；`git diff --check` 乾淨。

## 驗收

環境面失敗的 run 可經明確動作重跑 planning 並離開 define；內容面失敗不被繞過；resume 回傳 reason 與合法動作集合；abandon 後可重新 claim；恢復動作有稽核紀錄且重送冪等。
