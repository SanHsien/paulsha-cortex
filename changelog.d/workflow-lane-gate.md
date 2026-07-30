### Fixed
- **Issue #264：workflow phase job 收工不再誤走 slice lane gate**：completion sweep 新增
  `_is_workflow_lane_job()`，以 `workflow_run_id` 機械判定 lane 歸屬；帶 `workflow_run_id`
  的 phase job（本就不註冊進 `slices` 表）不再被查 `slices` 表、不再誤判為
  `needs_human`/`missing-slice-proof`，改記 `gate_status="workflow-tracked"`／
  `gate_reason="workflow-lane-job"`。`missing-slice-proof` 保留給真正屬於 slice lane 但
  關聯缺失的情形，並以 regression test 釘死其 fail-closed 行為未被放寬。
