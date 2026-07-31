### Fixed
- **Issue #286：fanout plan pinning 以 spec 檔自身所在 repo 解析**：修復
  `coordinator/autonomy.py` 中 `_infer_repo_root(spec_path)` 於 `PSC_REPO_ROOT`
  環境變數存在時盲目回傳 manager host repo 的問題。調整為優先以 `spec_path`
  所在目錄向上推導專案 Git repository root；當 spec 位於 manager host 外部的
  其他 repository（如 `serialwrap` 或 worktree）時，能正確將 relative plan glob
  解析至該專案目錄，解決跨 repo ad-hoc 派工觸發 `DispatchReadyError: plan file unreadable`
  的問題，並使 `ready` 與 `fanout` 階段對專案 repo_root 的判定維持一致。
