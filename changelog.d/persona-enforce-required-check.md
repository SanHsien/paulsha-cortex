### Changed
- **Issue #135：persona enforcement shadow → enforce**：切換前先以
  `python -m paulsha_cortex.persona.replay`（新增，可重跑）回放最近 50 個已合併
  PR 的實際檔案清單，證明對現行 `builder` 派工慣例零誤殺（578 個檔案、0 誤殺），
  才把 `paulsha_cortex/persona/personas.yaml` 的 `enforcement` 由 `shadow` 切為
  `enforce`。`persona-scope.yml`（`scope_ci.py`）現依 `enforcement` 動態決定放行：
  違規時輸出含 `role`／`violations[].path`／`violations[].rule_id`+`reason` 的可
  定位 verdict 並 `exit 1`；套用 `policy-exempt:persona-scope` label 時不阻擋，但
  違規內容仍完整輸出（不靜音，供事後稽核）。`.github/workflows/persona-scope.yml`
  新增 PR label 傳遞（`PERSONA_SCOPE_PR_LABELS`）並更新註解反映 enforce 現況。
  `persona-scope` 設為 main required status check 屬 GitHub repo 設定變更，本 PR
  不直接更動，設定步驟見 `docs/persona-scope-enforcement.md`。
