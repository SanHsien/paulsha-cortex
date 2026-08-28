### Fixed
- `paths.repo_root()` 未宣告 `PSC_REPO_ROOT` 時不再靜默退回 `Path.cwd()`。Windows service 的工作目錄正是 operator 的真實 checkout，於是「解析不出目標 repo」以前不是失敗，而是把 `git fetch`／`worktree remove` 打在 operator 的工作區。新增 `configured_repo_root()`（回報「有沒有宣告」）與 `repo_root(allow_cwd=True)`（operator 手動 CLI 顯式表態），daemon 側一律 fail-closed。取自上游 `59a7a9b`（#630／#612）。
- 測試側比照 `PSC_AGENTS_ROOT` 把 `PSC_REPO_ROOT` 指向 per-test 暫存路徑；三個 `recover-pre-candidate` 測試與 `init-sample` 測試因此改為自備 fixture repo／policy——它們以前是在真 checkout 上跑 `git worktree list`（同一條路徑再走一步就是 `git worktree remove --force`）。
