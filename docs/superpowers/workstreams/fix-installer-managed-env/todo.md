---
status: accepted
work_item: fix-installer-managed-env
---

# fix-installer-managed-env Todo

## Tasks

- [ ] `preserve_existing` 移除 `PSC_PROJECT_CONFIG_ROOT`（含既有 env 遷移語意）
- [ ] `PSC_CONTROL_ROOT` 納入 managed_env 且不得進 preserve_existing
- [ ] shell wrapper lock 路徑改用 Python path 契約，消除 shell/Python 解析分歧
- [ ] specs/coordinator root 的 per-instance 隔離納入驗收
- [ ] 回歸測試：雙 instance 相同與不同 agents_root 兩情境的 lock/specs 隔離
