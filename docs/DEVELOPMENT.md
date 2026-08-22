# 開發 paulsha-cortex（Windows-first）

## 技術基線

- Windows 11、PowerShell 7、Git for Windows。
- Python 3.10–3.13；日常與 Windows CI 使用 3.13。
- 原生 `.venv`，不要求 WSL 才能執行核心 runtime 或完整 pytest。
- 至少一個已安裝並登入的 executor CLI：`codex`、`claude` 或 `copilot`。

Linux/systemd 仍由 upstream 相容測試覆蓋；foreign-review 的 bubblewrap sandbox 仍是 Linux-only。這個限制只影響 Linux sandbox 隔離能力，不再阻擋 Windows 上的 manager、monitor、launcher、workflow、review evidence 與 service lifecycle。

## 第一次設定

在 Windows PowerShell 執行：

```powershell
pwsh -File tools/bootstrap_dev.ps1
```

腳本會建立 repo-local `.venv`，安裝 editable package、pytest、build 與 twine。若系統有 Python Launcher，預設選 Python 3.13；否則使用 PATH 上的 Python 3.10+。

## 驗證

原生 Windows 完整 gate：

```powershell
pwsh -File tools/dev_check.ps1
```

快速 platform smoke：

```powershell
pwsh -File tools/dev_check.ps1 -Quick
```

完整 gate 依序執行：

1. `git diff --check`
2. Python bytecode compile
3. 原生 Windows 全套 pytest
4. wheel/sdist build
5. `twine check --strict`

Linux 開發者仍可使用 `tools/bootstrap_dev.sh` 與 `tools/dev_check.sh`。兩邊都必須遵守 `CLAUDE.md` 的 changelog、PR context、Candidate 與 review evidence 契約。

## Windows service/runtime

Windows 不使用 systemd，也不要求提升權限建立 Scheduled Task。Installer 會在目前使用者的 Startup 目錄建立 `paulsha-cortex-<instance>.cmd`，登入時由它以隱藏背景程序啟動 manager 與 monitor；PID、lock、manifest 和 log 由 Cortex 自己管理。

```powershell
cortex service install --instance cortex --repo-root (git rev-parse --show-toplevel)
cortex service start --instance cortex --json
cortex service status --instance cortex --json
cortex service logs --instance cortex -n 50
cortex service restart --instance cortex --json
cortex service uninstall --instance cortex --purge --json
```

Stop/restart 在送出 `taskkill` 前會用 process command line 驗證 PID 確實屬於該 instance/component；stale PID 不會被盲目終止。

## Windows checkout 與 symlink

`.gitattributes` 強制文字檔使用 LF，保護仍保留的 Bash/systemd 相容檔案。upstream 將 `AGENTS.md`、`GEMINI.md` 與 `.github/copilot-instructions.md` 記錄為指向 `CLAUDE.md` 的 Git symlink；Windows 若未啟用 Developer Mode，可能呈現為只含 `CLAUDE.md` 的一般檔案，不要編輯或提交這些鏡像。

## 目錄

| 路徑 | 用途 |
| --- | --- |
| `paulsha_cortex/` | CLI、coordinator、monitor、persona、delivery 與治理契約 |
| `tests/` | 單元、整合、workflow 與 Windows regression tests |
| `.cortex/` | Cortex 自身的工作流設定與控制資料 |
| `openspec/` | active／archived 規格變更 |
| `docs/` | onboarding、架構、決策、review 與 fork 維護文件 |
| `reports/` | verification 與 independent review evidence |
| `changelog.d/` | 每個 PR 必備的 changelog fragment |
| `tools/` | Windows-first bootstrap 與一致驗證入口 |
| `.github/` | Windows/Linux CI、policy、CodeQL 與協作模板 |

## 變更流程

1. 從最新 `main` 建立 `feature/<slug>`；不要直接 commit 到 `main`。
2. 行為變更先補 regression test，再做最小修正。
3. 同一 PR 新增 `changelog.d/<slug>.md`，同步更新 `CHANGELOG.md` 的 `[Unreleased]`。
4. 執行 `pwsh -File tools/dev_check.ps1`。
5. 依 `CLAUDE.md` 帶完整 PR context 執行 policy check。
6. Review 必須綁定最新 Candidate；process exit 0 或 agent 自報通過不能取代 evidence。

## 依賴新鮮度：紅燈的兩條正當出口

每月的檢查比對**宣告**與 PyPI 現行版。當某個下限**不該**跟著現行版走時，只有兩種留下理由的做法：

- **維持宣告**：宣告那一行加 `# freshness-hold: <理由>`（長期政策，例如「這個下限就是我們要的」）。
- **已延後**：`.github/dependency-deferrals.json` 加
  `{"deferredLatest": "<當時看到的版本>", "reason": "<為什麼這次不升>"}`；PyPI 一超過該版本，
  延後自動失效、報告恢復提醒。沒有 `deferredLatest` 的條目直接忽略——那等於永久靜音，不是延後。

**不要用調高下限的方式讓紅燈消失**：宣告是相容性承諾，不是消音鍵。
