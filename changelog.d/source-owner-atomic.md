### Fixed

- **Issue #217：source-owner 轉移原子化**：`work_bridge.start_canonical_workflow` 新增顯式斷言——同 repo 下若有其他 work_id 的 ongoing WorkflowRun 其 `issue_refs` 與本次 `mapped_issues` 重疊，且該 run 尚未 terminal（`status` 不在 `{superseded, done}`），一律拒絕新 claim，避免 hippo #41 v3→v4 owner 轉移競態重現的 `missing_issue`/`human-intervention-required` run。`claim.load_work_authorities` 同步補上「同一 repo 下每個 issue 至多一個 work_id owner」的結構性不變量，讓轉移中途若快照仍出現雙 owner，任何 claim/ship/abandon 呼叫都會在載入 authority 時即拒絕，而非悄悄挑一個贏家。
