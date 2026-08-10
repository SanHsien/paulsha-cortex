---
status: accepted
work_item: fix-deck-verification-skeleton
---

# fix-deck-verification-skeleton Todo

## Tasks

- [ ] `_verification_skeleton` 從 `.project-policy.yml` 的 `preflight.steps` 導出 checks/tests/full_suite argv
- [ ] 偵測不到 policy steps 時填 fail-closed placeholder 與醒目 warning（不留空）
- [ ] `name: "policy"` 保留、argv 改 policy_check；同步修 docs 樣板與 init-sample 陳舊提示
- [ ] 回歸測試涵蓋「有 preflight.steps」與「無 policy 檔」兩型 repo
