## 變更摘要

請說明動機、治理契約／使用者可見結果與主要實作。

## Candidate 與驗證

- Candidate commit：
- Verification command／result：
- Independent review evidence：

- [ ] `pwsh -File tools/dev_check.ps1`
- [ ] 已以本 PR 的 title/body/labels/base/head 執行 `CLAUDE.md` 指定的 policy check
- [ ] Verification 與 Review 都綁定上方同一 Candidate

## 專案契約

- [ ] 分支符合 `feature/<slug>` 或 `wt/<feature>/<subtask>`
- [ ] 若對應 issue，PR body 使用 `Closes`／`Fixes`／`Resolves #N`
- [ ] `changelog.d/<slug>.md` 已新增並 commit
- [ ] `CHANGELOG.md` `[Unreleased]` 已同步
- [ ] 沒有把 agent 自報、process exit 0 或 PR 存在當作完成證據
- [ ] 沒有放寬 Candidate、sandbox、secret、worktree 或 remote Git 邊界

## 文件與風險

- [ ] README／相關 docs 已同步，或已說明不需要更新
- [ ] 已說明 platform、retry、recovery、token／API 成本與未完成風險
- [ ] 沒有加入個人絕對路徑、token、私有資料或 agent session
