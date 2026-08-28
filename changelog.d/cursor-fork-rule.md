### Added
- `.cursor/rules/no-upstream-pr.mdc`：Cursor 的規則是 per-project 的，補上「對外只打本 fork」——每個 clone 先 `gh repo set-default SanHsien/paulsha-cortex`，開 PR 明寫 `--repo/--base/--head` 並讀輸出 URL 確認 owner；回貢上游要維護者當次對話明確同意。內容與 `docs/FORK.md`、Codex 與 Antigravity 的全域規則一致。
