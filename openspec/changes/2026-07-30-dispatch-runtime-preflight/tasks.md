---
status: accepted
work_item: dispatch-runtime-preflight
---

# Tasks

- [ ] 1.1 RED：依 `docs/superpowers/plans/dispatch-runtime-preflight.md` 的 TDD RED 章節新增測試，確認失敗。
- [ ] 1.2 實作至 GREEN，範圍限於 `docs/superpowers/specs/dispatch-runtime-preflight-spec.md` 的 Requirements。
- [ ] 1.3 `changelog.d/dispatch-runtime-preflight.md` fragment 與 `CHANGELOG.md [Unreleased]` entry（#262）。
- [ ] 1.4 `python3 -m pytest tests/ -q` 全綠；帶 PR 上下文的 `policy_check` 0 fail；`git diff --check` 乾淨。

## 驗收

缺 pytest／socat 的 fixture 在 dispatch 前被攔截且 model invocation 為 0；preflight 與正式 job 環境一致；stale degraded 不被當成 fresh hard block；probe 有 timeout／cache／rate-limit 預算。
