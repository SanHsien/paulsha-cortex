### Fixed
- **Issue #270：CLAUDE.md 的 changelog 要求對齊 engine R-09**：agent 指引原先只要求
  `CHANGELOG.md [Unreleased]`，與 R-09 實際檢查的 `changelog.d/*.md` fragment 不一致，
  照做必掛 `policy / check`（#266／#267／#268／#269 四個 PR 實證）。改以 fragment 為硬性
  gate 並寫明檔名 slug 慣例與「須 commit 才進 diff」；claim-done checklist 的 policy_check
  補上帶 PR 上下文的完整命令（裸跑會給出假的 `fail: 0`）；移除指向不存在的
  `.github/pull_request_template.md` 的懸空引用。
