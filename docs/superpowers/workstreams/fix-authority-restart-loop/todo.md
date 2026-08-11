---
status: accepted
work_item: fix-authority-restart-loop
---

# fix-authority-restart-loop Todo

## Tasks

- [ ] `_manager_reset_workflow_for_authority_restart` 同步更新 claim_key（或觸發改冪等/一次性）
- [ ] source_revision 改寫時 rebind/invalidate 對應 job
- [ ] manager_daemon resume 迴圈守衛補 needs_human（縱深防禦）
- [ ] 回歸測試重現「剝除 facet → 放行 → mismatch → 寫回」三步迴圈並驗證收斂
