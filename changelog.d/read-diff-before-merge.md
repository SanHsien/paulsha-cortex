# 合併前必讀 diff

- `CLAUDE.md` 的「完成任務（claim done）前」新增一條：按下 merge 前必須讀過完整 diff，包含 Dependabot 開的。CI 綠燈證明的是測試沒紅，不是「改了什麼、該不該進 main」；lockfile 的連鎖升級、transitive major 與跨出宣告範圍的變更只有讀 diff 看得到。
- 規則寫進 canonical 的 `CLAUDE.md`（`AGENTS.md`／`GEMINI.md`／`copilot-instructions.md` 為指向它的 symlink），所以對所有 agent 一致生效。
