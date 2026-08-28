# 貢獻 paulsha-cortex

歡迎改善 agent 工程治理、狀態契約、verification、review independence、worktree lifecycle、測試與文件。參與前請遵守 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)。

## 開始之前

- 先搜尋本 fork 與 [upstream issues](https://github.com/hamanpaul/paulsha-cortex/issues)。
- 通用缺陷優先確認是否適合回饋 upstream；本 fork 特有的 Windows／WSL 開發體驗可直接在本 fork 提案。
- 大型架構、安全、completion authority 或 state transition 變更先開 issue。
- 安全漏洞依 [`SECURITY.md`](SECURITY.md) 私下回報。
- 先閱讀 [`docs/FORK.md`](docs/FORK.md) 的授權與 production 採用限制。

## 開發環境

```powershell
git clone https://github.com/SanHsien/paulsha-cortex.git
cd paulsha-cortex
pwsh -File tools/bootstrap_dev.ps1
pwsh -File tools/dev_check.ps1 -Quick
```

原生 Windows 11 是本 fork 的權威開發 runtime；PowerShell 腳本直接使用 repo-local `.venv`。WSL 只用於 Linux/systemd/bubblewrap 相容驗證。完整說明見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。

## Pull request

1. 從 `main` 建立 `feature/<slug>`，一個 PR 聚焦一個主題。
2. 行為變更先補 regression test。
3. 新增並 commit `changelog.d/<slug>.md`，同步更新 `CHANGELOG.md` `[Unreleased]`。
4. 執行完整 dev check，以及 `CLAUDE.md` 指定的 PR-context policy check。
5. 說明 Candidate SHA、實際執行的測試、review evidence、平台限制與未完成風險。

不要以 agent 自報、process exit 0、PR 已建立或過期 Candidate 的 review 取代完成證據。
