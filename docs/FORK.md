# Fork 維護說明

最後評估：2026-08-22

本 repository 是 [`hamanpaul/paulsha-cortex`](https://github.com/hamanpaul/paulsha-cortex) 的 GitHub fork。定位是 **Windows-first development fork**：用於研究、開發與驗證多 Agent 工程治理，不宣稱已可直接承載 production 自主循環。

## 為什麼保留這個 fork

- Candidate、Verification、Independent Review、Delivery 與 CompletionRecord 的一致性模型，直接對應多 agent／worktree／retry 情境最容易失真的治理缺口。
- upstream 有實際 Python runtime、GitHub delivery、manager daemon、monitor、persona 與大量 regression tests，不是概念展示。
- 本 fork 已把核心 runtime、service lifecycle、monitor transport、process launcher 與完整 pytest 補成原生 Windows-first 路徑，同時保留 Linux/systemd 相容性。
- fork 另維護 Windows service backend、loopback TCP monitor transport、process / file durability、PowerShell bootstrap、Windows regression coverage、CodeQL、dependency freshness 與 upstream tracking。

## 採用限制

- **授權仍未明確**：截至 2026-08-22，upstream 根目錄仍沒有 `LICENSE`。GitHub fork 機制不等於取得一般性的再散布、改作或套件發布授權；在 upstream 明確補授權前，不把衍生 wheel／sdist 發佈到 GitHub 以外，也不聲稱本 fork 是已確認授權的開源發行版。
- **不是 production-ready 宣稱**：CI 綠燈只證明目前測試契約成立，不等於多 Agent 自主循環已具 production 保證。
- **Windows / Linux 能力不完全對稱**：foreign-review 的 bubblewrap 隔離仍需 Linux；Windows 會明確略過這個 POSIX-only sandbox，不把它誤報為已驗證。
- **upstream 仍快速演進**：本 fork 採選擇性同步，不能把 upstream `main` 整批 merge 當作例行更新。
- 目前主要 commit 歷史仍集中於少數維護者；fork 必須保有獨立復原、CI 與 upstream ledger。

## 目前 fork 差異

相對共同 baseline，本 fork 的主要增量包括：

- Windows 11 per-user Startup service backend。
- loopback TCP monitor transport。
- Windows process wrapper、PID / lock / durability / path safety 修補。
- PowerShell bootstrap 與 canonical development gate。
- Windows-specific regression tests 與 GitHub Actions / CodeQL。
- dependency freshness 與 upstream release tracking。
- 多項 executor auth、retry / recovery、deck DX 與 verification reliability 修補。

完整技術差異仍以 Git history、tests 與 [`docs/UPSTREAM.md`](UPSTREAM.md) 為準；本文件只維護採用邊界，不複製完整 changelog。

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

逐項標記採用、部分採用、延後或不採用並記錄理由；不要把 upstream 整批變更直接併入有本 fork 差異的 `main`。同步後執行完整 gate，並更新 [`docs/UPSTREAM.md`](UPSTREAM.md) 的 review watermark。

### PR 只打本 fork

**PR、push、release 一律指向 `SanHsien/paulsha-cortex`。** 對 `hamanpaul/paulsha-cortex` 開 PR、
push 或發 release，需要主人在當次對話明確同意回貢；「fork 一份」「建開發環境」「比照其他 repo」
都不是同意。

根因是機制不是粗心：`gh` 在 fork clone 的**預設 repo 就是上游**——本 repo 的 clone 原本
`gh repo set-default --view` 回的就是 `hamanpaul/paulsha-cortex`，所以裸跑 `gh pr create` 必然打上去。

```powershell
gh repo set-default SanHsien/paulsha-cortex   # 每個 clone 先跑一次
gh repo set-default --view                    # 必須回 SanHsien/paulsha-cortex
gh pr create --repo SanHsien/paulsha-cortex --base main --head feature/<slug>
```

建完**讀輸出的 URL**，owner 必須是 `SanHsien`；不是就立刻 `gh pr close` 留言道歉說明開錯 repo，
再對 origin 重開。2026-08-22 就是在這裡誤開了 `hamanpaul/paulsha-cortex#787`（同日另一個工作階段
也在別的 fork 誤開一次）。批次跑多個 repo 時最容易略過確認，而那正是出事的場合。

**本 repo 是「日常直推 main」的例外**：其他 repo 的維護變更直接推 `origin/main`，但本 repo 的
policy CI 會檢查分支名 `feature/<slug>`、`changelog.d/<slug>.md` fragment 與 PR template checklist，
所以這裡仍走 branch → PR → CI → merge，只是 base 一定是 `SanHsien/paulsha-cortex`。

## 2026-08-22 水位快照

| 項目 | 值 |
| --- | --- |
| fork source version | `0.1.8` |
| upstream source version | `0.1.8` |
| 已同步共同 baseline | `dc8a968` |
| upstream `main` snapshot | `13366c0` |
| fork 與 upstream 的分岔量 | 不寫在這裡：每次 commit 都會變。由 `upstream-check` 每週跑出來（見 workflow run summary 的 **Fork status**），或本機跑 `python tools/check_upstream_updates.py` |
| 維護策略 | 202 個 post-v0.1.8 upstream commits 已批次檢視；等待下一個 upstream tag 再整批評估 |
| 決策 | 繼續維護 Windows-first development fork；授權與 Linux-only sandbox 邊界收斂前不列為 production-ready |

這些數字是日期快照，不是 README 的永久產品敘述。後續判斷時三種資料來源各有不同責任：

- [`docs/UPSTREAM.md`](UPSTREAM.md)：人工 review ledger，記錄已看過哪些 release / PR / issue、採用或延後理由與下一個 review watermark。
- `tools/upstream_baseline.json`：供自動 upstream-check 使用的 **reviewed-through / common baseline 記錄**；它不是即時 `upstream/main` snapshot，也不要求與本頁日期快照逐次同步。
- `upstream-check` 的 **Fork status**（每週一自動跑，也可本機執行 `python tools/check_upstream_updates.py`）／GitHub compare：查當下 fork 與 upstream `main` 的即時 ahead / behind 與 commit 差異。**這類數字不進文件**——它隨每次 commit 變動，寫下的當下就開始過期；本頁只保留穩定的 SHA 與決策。

不要把其中任一來源單獨解讀成完整的 upstream truth。
