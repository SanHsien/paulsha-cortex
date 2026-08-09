# 開發 paulsha-cortex

## 技術基線

- Python 3.10–3.13；本 fork 以 `.python-version` 固定日常開發為 3.13。
- `uv` 管理隔離環境與開發依賴。
- WSL2／Linux 是權威 runtime 與測試環境。
- GitHub CLI、Git worktree，以及實際使用的 agent executor。
- 完整 foreign-review sandbox 另需 `bubblewrap`、`socat` 與 upstream README 指定的 sandbox runtime。

原生 Windows 不提供 `fcntl` 與 `os.getloadavg`，因此不能作為全套 pytest 或 manager daemon 的權威環境。PowerShell 腳本只提供一致入口，實際工作在 WSL 執行。

## 第一次設定

從 Windows PowerShell 執行：

```powershell
pwsh -File tools/bootstrap_dev.ps1
```

如需指定 distribution：

```powershell
pwsh -File tools/bootstrap_dev.ps1 -Distribution Ubuntu
```

腳本會在 WSL 的 `${XDG_CACHE_HOME:-$HOME/.cache}/paulsha-cortex/venvs/` 建立 repo 專屬 venv，避免把大量小檔案放進 OneDrive 或 `/mnt/c`。若缺少 production sandbox 套件，bootstrap 會警告，但不阻擋核心開發。

若大量修改或反覆執行全套測試，建議直接把第二份工作 clone 放在 WSL Linux filesystem；`/mnt/c` 的 metadata I/O 會顯著拖慢 pytest。Windows clone 保留作 GitHub／PowerShell 整合入口即可。

## 驗證

日常完整 gate：

```powershell
pwsh -File tools/dev_check.ps1
```

快速 smoke：

```powershell
pwsh -File tools/dev_check.ps1 -Quick
```

WSL 內也可直接執行：

```bash
tools/bootstrap_dev.sh
tools/dev_check.sh
```

完整 gate 依序檢查 diff whitespace、shell script CRLF、Python bytecode、全套 pytest 與 wheel/sdist build。PR 仍須依 `CLAUDE.md` 帶完整 PR context 執行 policy check；裸跑 policy check 不是完成證據。

## Windows checkout 與 symlink

`.gitattributes` 強制文字檔使用 LF，避免 Bash script 在 WSL 以 `pipefail: invalid option name` 失敗。

upstream policy 將 `AGENTS.md`、`GEMINI.md` 與 `.github/copilot-instructions.md` 記錄為指向 `CLAUDE.md` 的 Git symlink。Windows 若未啟用 Developer Mode，checkout 可能將它們呈現成只含 `CLAUDE.md` 的一般檔案；不要編輯或提交這些鏡像。Linux CI 的 symlink checkout 與 policy gate 才是權威結果。

## 目錄

| 路徑 | 用途 |
| --- | --- |
| `paulsha_cortex/` | CLI、coordinator、monitor、persona、delivery 與治理契約 |
| `tests/` | 單元、整合、workflow 與 regression tests |
| `.cortex/` | Cortex 自身的工作流設定與控制資料 |
| `openspec/` | active／archived 規格變更 |
| `docs/` | onboarding、架構、設計、決策與 fork 維護文件 |
| `reports/` | verification 與 independent review evidence |
| `changelog.d/` | 每個 PR 必備的 changelog fragment |
| `tools/` | Windows/WSL bootstrap 與一致驗證入口 |
| `.github/` | 測試、policy、CodeQL、Dependabot 與協作模板 |

## 變更流程

1. 從最新 `main` 建立 `feature/<slug>`；不要直接 commit 到 `main`。
2. 行為變更先補 regression test，再做最小修正。
3. 同一 PR 新增並 commit `changelog.d/<slug>.md`，同步更新 `CHANGELOG.md` 的 `[Unreleased]`。
4. 執行 `pwsh -File tools/dev_check.ps1`。
5. 依 `CLAUDE.md` 帶 PR title/body/labels/base/head 執行 policy check。
6. Review 必須綁定最新 Candidate；process exit 0 或 agent 自報通過都不能取代 evidence。
