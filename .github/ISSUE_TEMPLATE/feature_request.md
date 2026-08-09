---
name: 功能建議
about: 提出 agent 工程治理與開發體驗改進
title: "[Feature] "
labels: enhancement
assignees: ""
---

## 想解決的治理問題

請描述目前哪個 authority、artifact、state transition 或 operator action 不足。

## 建議契約

請描述輸入、輸出、不可變識別、失敗狀態、retry／recovery 與完成條件。

## 邊界確認

- [ ] 不以 agent 自報或 process exit 0 取代驗證。
- [ ] Verification／Review 綁定 exact Candidate。
- [ ] 不放寬 sandbox、secret、worktree 或 remote Git 邊界。
- [ ] 有明確的 fail-closed、needs-human 或復原路徑。
- [ ] 已考慮 token、GitHub API 與重試成本。

## 替代方案

請說明目前的手動流程與不採用其他方案的原因。
