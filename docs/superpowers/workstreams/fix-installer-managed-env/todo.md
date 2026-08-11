---
status: accepted
work_item: fix-installer-managed-env
---

# fix-installer-managed-env Todo

## Tasks

- [x] `preserve_existing` 移除 `PSC_PROJECT_CONFIG_ROOT`（含既有 env 遷移語意）——遷移語意用
      `cortex doctor` 的 `managed-path-drift` probe 承接（鍵缺席＝過渡態 warn，鍵存在但值錯
      才 fail），installer 端不做隱含 auto-migrate，reinstall 一律用目前 `PSC_AGENTS_ROOT`
      重新推導覆寫。
- [x] `PSC_CONTROL_ROOT` 納入 managed_env 且不得進 preserve_existing（`<agents_root>/control/<instance>`，
      比照 `PSC_RUN_ROOT` 的 `run/<instance>`）
- [x] shell wrapper lock 路徑改用 Python path 契約，消除 shell/Python 解析分歧——新增
      `cortex control lock-path`，`service-manager.sh` 的 `manager_lock_path()` 改為委派並快取
- [x] specs/coordinator root 的 per-instance 隔離納入驗收——評估後決定 `PSC_MANAGER_SPECS_DIR`／
      `PSC_COORDINATOR_ROOT`／`PSC_SPECS_ROOT` 暫留 operator 域（牽動面遠大於本次範圍，
      coordinator_root 是 jobs.json/delivery-journal 等大量既有呼叫點的共用 state root），
      以 pin 測試（`test_install_leaves_specs_and_coordinator_roots_as_operator_domain`）與
      README／code comment 記錄決策，留後續 follow-up
- [x] 回歸測試：雙 instance 相同與不同 agents_root 兩情境的 lock/specs 隔離——見
      `test_install_two_instances_under_shared_agents_root_get_distinct_control_roots`、
      `test_two_instances_with_distinct_agents_root_get_distinct_lock_paths`

## 完成紀錄（issue #371／#375 合併修復）

`installer.py` 的 `managed_env`／`preserve_existing`、新增 `paulsha_cortex/control/cli.py`、
`service-manager.sh` 的 `manager_lock_path()`、`doctor.py` 的 `managed-path-drift` probe。
新增 19 個回歸測試，修正前皆已確認 RED（`test_install_preserves_existing_operator_env_lines`
直接重現 #371 實測的 hippo instance 場景）。詳見 `changelog.d/installer-managed-env.md`。
