### Added

- **Issue #214：stage 級 content-addressed execution key**：新增 `registry.compute_stage_execution_key`（涵蓋 repo/work_id/card/phase/executor/model/base_sha/candidate_sha/frozen_input_hashes/action/test_policy）與 `JobRegistry.find_reusable_stage_evidence`（fail-closed reuse 查詢，建立在既有 phase 級 checkpoint 之上、與 `bind_workflow_evidence` 並存不改語意），`manager_daemon.py` 的 workflow-action/start 觸發處可消費此查詢在相同 key 已有可重用 evidence 時短路 dispatch、不增加 model invocation；`CompletionRecord` 新增 `reused_from`（run/job/evidence hash）provenance 欄位，並排除在 semantic match 之外避免良性 reuse 誤觸衝突 quarantine。
