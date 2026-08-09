# Fork 維護說明

最後評估：2026-08-09

本 repository 是 [`hamanpaul/paulsha-cortex`](https://github.com/hamanpaul/paulsha-cortex) 的 GitHub fork。定位是研究、開發與驗證 agent 工程治理，不宣稱已可直接承載 production 自主循環。

## 為什麼保留這個 fork

- Candidate、Verification、Independent Review、Merge Result 與 CompletionRecord 的一致性模型，直接對應多 agent／worktree／retry 情境的治理缺口。
- upstream 有實際 Python runtime、GitHub delivery、manager daemon、monitor、persona 與大量 regression tests，不是概念展示。
- upstream 在 2026-08-08 發布 v0.1.4，維護與修正節奏活躍。
- 本 fork 已把核心 runtime、service lifecycle、monitor transport、process launcher 與完整 pytest 移植為原生 Windows-first，同時保留 Linux/systemd 相容性。

## 採用限制

- 評估時 upstream 根目錄沒有 LICENSE。GitHub fork 機制不等於取得一般性的再散布、改作或套件發布授權；在 upstream 明確補授權前，不把衍生套件發佈到 GitHub 以外，也不聲稱本專案是已確認授權的開源發行版。
- foreign-review 的 bubblewrap 隔離仍需 Linux；Windows 會明確略過這個 POSIX-only sandbox，不把它誤報為已驗證。
- 最新公開 issues 包含 verification evidence 可被 rigged、自報測試與實測背離、retry dead-end、handoff 殘留與 GitHub rate-limit 協調問題。production 採用前必須逐項重新評估，不能只看 CI 綠燈。
- 目前主要 commit 歷史集中於單一維護者，fork 需保有獨立復原與上游追蹤能力。

## Remote 契約

```text
origin   https://github.com/SanHsien/paulsha-cortex.git
upstream https://github.com/hamanpaul/paulsha-cortex.git
```

開始上游評估時：

```powershell
git fetch upstream main --tags --prune
git log --oneline main..upstream/main
gh issue list --repo hamanpaul/paulsha-cortex --state open --limit 20
gh pr list --repo hamanpaul/paulsha-cortex --state all --limit 20
```

逐項標記採用、部分採用、延後或不採用並記錄理由；不要把 upstream 整批變更直接併入有本 fork 差異的 `main`。同步後執行完整 gate，並更新 `docs/DECISIONS.md` 的水位。

## 初始水位

| 項目 | 值 |
| --- | --- |
| upstream tip | `b868760` |
| release | `v0.1.4` |
| 評估日期 | 2026-08-09 |
| 決策 | 值得維護為 Windows-first development fork；授權與 Linux-only sandbox 邊界收斂前不列為 production-ready |
