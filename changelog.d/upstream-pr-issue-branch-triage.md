### Changed
- `docs/UPSTREAM.md` 補上上游 PR／issue／分支的分流規則與水位（PR #764、issue #781，分支盤點日 2026-08-22）。重點：274 個分支中有 66 個相對 `main` 帶獨佔 commit，但那是 squash merge 的假象——實測三條最舊的分支，修正都已在 `main` 且本 fork 已有其測試檔；判斷方式是用 issue 編號到 `main` 搜一次。
