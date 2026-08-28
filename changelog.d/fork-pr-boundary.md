### Changed
- `docs/FORK.md` 新增「PR 只打本 fork」：`gh` 在 fork clone 的預設 repo 是上游，每個 clone 要先 `gh repo set-default SanHsien/paulsha-cortex`，開 PR 明寫 `--repo/--base/--head` 並確認輸出 URL 的 owner；對上游開 PR 需要維護者當次對話明確同意。同時寫明本 repo 因 policy CI 而維持 branch → PR → CI 流程，是「日常直推 main」的例外。
