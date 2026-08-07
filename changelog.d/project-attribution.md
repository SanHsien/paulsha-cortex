### Fixed
- **paulshaclaw#264：status 條目補上明確 project 歸屬**：`recent_done` 從 completion manifest 的 `work_authority.repo` 投影 `repo`；`attention`／`slices` 從明確的 slice 或 workflow job repo 投影，沒有資料時保留 `null`，不從 worktree 路徑猜測。
