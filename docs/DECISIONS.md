# paulsha-cortex 現行決策

最後修訂：2026-08-09

本檔只保留仍影響本 fork 維護與實作的取捨。操作步驟見 [`DEVELOPMENT.md`](DEVELOPMENT.md)，來源與同步方法見 [`FORK.md`](FORK.md)，版本歷史見 [`CHANGELOG.md`](../CHANGELOG.md)。

## 1. 保留 GitHub fork 關係

- `origin` 指向 `SanHsien/paulsha-cortex`，`upstream` 指向 `hamanpaul/paulsha-cortex`。
- 目前不改產品名稱、不重寫歷史、不離開 fork network；先保留低成本追蹤 upstream 的能力。
- 初始評估水位為 upstream `b868760`／v0.1.4。每次同步只從這個水位之後評估，並更新本節。

## 2. 定位為 research/development fork

- 值得投資的核心是 artifact-backed state transition、exact Candidate verification、independent review 與 completion authority，不是增加 agent 數量。
- 在公開高嚴重度 issues、授權與平台邊界收斂前，不把 CI success、agent 自報或 PR 存在視為 production readiness。
- 若本 fork 修正通用缺陷，優先整理為可回饋 upstream 的小型 PR；個人工作流偏好留在 fork 文件或薄包裝層。

## 3. WSL/Linux 是權威環境

- PowerShell 是 Windows 使用者入口；pytest、build、manager daemon 與 sandbox 驗證在 WSL/Linux 執行。
- `.gitattributes` 強制 LF，避免 Windows `core.autocrlf=true` 破壞 Bash scripts。
- venv 放在 WSL cache，不放 OneDrive；高頻全測建議使用 WSL Linux filesystem 的工作 clone。
- 原生 Windows collection failure 不以 mock 掩蓋，也不宣稱 Windows runtime support。

## 4. 不替 upstream 擅自決定授權

- 評估水位沒有 LICENSE；本 fork 不新增一張看似涵蓋 upstream 程式碼的授權檔。
- GitHub 內 fork、研究與修正不延伸解讀成任意再散布權。在 upstream 補授權或取得作者明確同意前，不對外發佈衍生 wheel／sdist。
- 新增貢獻與安全政策只描述協作方式，不更改既有程式碼的著作權狀態。

## 5. 驗證仍由 repo 契約決定

- `tools/dev_check.ps1`／`.sh` 是一致入口，不取代 `CLAUDE.md` 的 changelog、PR-context policy check 與 Candidate evidence 規則。
- 每次只接受同一 Candidate 的一次權威 full gate；失敗後只重跑受影響的 focused test，再做一次完整收尾。
- WSL `/mnt/c` 的慢速不是測試失敗；但 timeout 或 skipped checks 必須如實記錄，不能包裝成通過。
