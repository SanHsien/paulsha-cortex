# paulsha-cortex 現行決策

最後修訂：2026-08-11

本檔只保留仍影響本 fork 維護與實作的取捨。操作步驟見 [`DEVELOPMENT.md`](DEVELOPMENT.md)，來源與同步方法見 [`FORK.md`](FORK.md)，版本歷史見 [`CHANGELOG.md`](../CHANGELOG.md)。

## 1. 保留 GitHub fork 關係

- `origin` 指向 `SanHsien/paulsha-cortex`，`upstream` 指向 `hamanpaul/paulsha-cortex`。
- 目前不改產品名稱、不重寫歷史、不離開 fork network；先保留低成本追蹤 upstream 的能力。
- 初始評估水位為 upstream `b868760`／v0.1.4。每次同步只從這個水位之後評估，並更新本節。
- 最新已評估水位為 upstream `b79c74a`／v0.1.5；逐 PR 決策與下次起點見 [`UPSTREAM.md`](UPSTREAM.md)。

## 2. 定位為 research/development fork

- 值得投資的核心是 artifact-backed state transition、exact Candidate verification、independent review 與 completion authority，不是增加 agent 數量。
- 在公開高嚴重度 issues、授權與平台邊界收斂前，不把 CI success、agent 自報或 PR 存在視為 production readiness。
- 若本 fork 修正通用缺陷，優先整理為可回饋 upstream 的小型 PR；個人工作流偏好留在 fork 文件或薄包裝層。

## 3. 原生 Windows 是本 fork 的第一級環境

- PowerShell、repo-local `.venv`、native manager/monitor、Windows Startup service backend 與 Windows CI 是權威開發路徑。
- POSIX `fcntl`、directory fsync、Unix socket、process signal 與 mode semantics 均有顯式 platform adapter，不在 import/collection 階段假設 Linux。
- `.gitattributes` 仍強制 LF，保護跨平台 evidence hash 與保留的 Bash/systemd 相容檔案。
- Linux/systemd 保持支援；bubblewrap foreign-review sandbox 明確列為 Linux-only，不偽裝成 Windows 已具備的隔離保證。

## 4. 不替 upstream 擅自決定授權

- 評估水位沒有 LICENSE；本 fork 不新增一張看似涵蓋 upstream 程式碼的授權檔。
- GitHub 內 fork、研究與修正不延伸解讀成任意再散布權。在 upstream 補授權或取得作者明確同意前，不對外發佈衍生 wheel／sdist。
- 新增貢獻與安全政策只描述協作方式，不更改既有程式碼的著作權狀態。

## 5. 驗證仍由 repo 契約決定

- `tools/dev_check.ps1`／`.sh` 是一致入口，不取代 `CLAUDE.md` 的 changelog、PR-context policy check 與 Candidate evidence 規則。
- 每次只接受同一 Candidate 的一次權威 full gate；失敗後只重跑受影響的 focused test，再做一次完整收尾。
- WSL `/mnt/c` 的慢速不是測試失敗；但 timeout 或 skipped checks 必須如實記錄，不能包裝成通過。

## 6. Issue #442 採 ship-phase executor auth canary

- `cg` 維持 zero-tool，只能用於 read-only planning／review；Windows 由 typed-argv Python wrapper 經 stdin 傳 prompt，不退回 Bash wrapper。
- `provider:executor` 只先啟用於 `openspec-archive`／`policy-commit`。在 GitHub side effect 前檢查登入態、可用時依既有 identity 順序 reroute，全部不可用才進 `needs_human`。
- 不自動從 `gh` keyring 抽取 Copilot token，也不把 token 寫入 repository。只有 deployment runtime env 已安全提供 `COPILOT_GITHUB_TOKEN`／`GH_TOKEN`／`GITHUB_TOKEN` 時才使用；自動 secret-store 整合需另案具備 rotation、ACL、redaction 與 restart 證據。

## 2026-08-29：上游檢查補上 PR 與 issue 兩個面向

**決定**：`check_upstream_updates.py` 補上以 `--state all` 收集上游 PR／issue 的邏輯，
`upstream-check.yml` 補 `GH_TOKEN: ${{ github.token }}`，新增 `tests/test_upstream_updates.py`。
Baseline 既有的水位不動。

**理由**：`docs/UPSTREAM.md` 早就寫著「四個面向都要看」，`upstream_baseline.json` 也記著
`reviewed_pr_through` 與 `reviewed_issue_through`——但**沒有任何程式讀那兩個欄位**，檢查器只比對
commit 水位。那兩個面向不是「查過沒發現」，是根本沒查，而每週的排程報告長得跟查過一樣綠。
這是艦隊層級的問題：24 個 fork 裡 21 個都這樣（`SanHsien/repo-fleet-ops` 的 `docs/INCIDENTS.md`
第十條）。參考實作是 `SanHsien/harness-guard`。

三個性質，缺一不可：

- **`--state all`**：只查 `open` 看不到「開了又關、沒有合併」的 PR，而那正是「上游拒收、但可能對
  本 fork 有價值」的一類——已合併的遲早會經由 commit 抵達，被關掉的永遠不會。
- **`gh` 失敗時回 `None` 不回 `[]`**，報告寫 `Not checked` 並 **fail closed**（exit 2）。
  「沒查到」和「沒有」在綠色報告裡長得一樣，只有一個是真的。
- **`GH_TOKEN`**：`gh` 在 Actions 裡沒有憑證就列舉不到，配上 fail closed 會讓紅燈的意思變成
  「檢查器壞了」而不是「上游有東西」。

**證據**：落地後實跑 `python tools/check_upstream_updates.py`，三個面向都印出水位與待辦數；
本 repo 的 gate 全綠。

**已知代價**：水位以上真的有東西時，每週的 upstream-check 會回 exit 1。那是它該做的事——先前的
綠燈不是「沒有待辦」，是沒有人看。

**觸發條件**：報告列出項目時逐筆讀 diff、把採用／略過理由寫進本檔，然後才推進 baseline 的水位。

**本 repo 額外一點**：這裡追蹤的是 release tag，兩個 release 之間 commit 軸本來就是空的——
而那正是「open PR 或 issue 是上游動態唯一可見處」的時候。所以 ticket 收集放在 release 判斷
**之外**，不能只在有新 tag 時才跑，否則那幾個月照樣看不見。


## 2026-08-30：上游 #788–#816 與 #799–#815 的判定（commit 水位不推進）

PR 水位 787 → 816；issue 水位 781 → 815。**commit 水位維持 `dc8a968`（v0.1.8）**——上游已發
v0.1.10，兩版之間 **358 個 commit** 尚未逐筆審，推進等於宣稱審過。

### 結論：這 17 個 PR 全部經由 release 軸抵達，不需要在 PR 軸另行決定

本 fork 的追蹤單位是 **release tag**（`track: release`）。17 筆裡：

- **12 筆已 merged**（`#788`／`#794`–`#798`／`#801`／`#804`／`#806`／`#809`／`#811`／`#816`）——
  依定義會進 `main`、隨下一個 release tag 抵達。
- **5 筆 CLOSED 未合併**（`#789`–`#793`）。這是本來最需要小心的一類（未合併就關閉的永遠不會經由
  commit 軸抵達），所以逐筆用它們 `Closes` 的 issue 編號回查 `upstream/main`：

| PR | Closes | 在 `upstream/main` 的落地 |
| --- | --- | --- |
| `#791` | `#716` | `4200012`（builder-workspace-write 改發 `-s danger-full-access`）、`0e91ed6`（出口網路管制） |
| `#792` | `#763` | `da32375`（recover-repair-commit gate ledger 缺席時 fail-closed） |
| `#793` | `#692` | `e22ef78`（HOME lstat traceback 洩漏）、`ad3f832`（downgraded job HOME fail closed） |
| `#789` | `#681` | commit 訊息查不到編號，但 **issue #681 狀態是 CLOSED / COMPLETED** |
| `#790` | `#695` | 同上，**issue #695 CLOSED / COMPLETED** |

也就是說這 5 筆是**改用別的 PR 重新落地**後被關掉的，不是被上游拒收——內容已經在 `main` 裡，
落在那 358 個 commit 的範圍內。這正是 `PLAYBOOK` 判準三講的 squash／re-land 假象：
`ahead` 不等於「有未合併的東西」，要用主旨或 issue 編號回查。

### issue 面向：12 筆都是上游自己的缺陷回報，修正走同一條 release 軸

`#799`–`#815` 全是上游 coordinator／porcelain／trust-root 的缺陷單（builder 卡零產出、
install service 整檔取代共享設定、verifier 在唯讀 sandbox 跑不綠、agy fallback 的 terminal
不可採信…）。本 fork **確實有** `paulsha_cortex/coordinator/`（47 檔）與 `porcelain/`（13 檔），
所以這些缺陷本線多半也有；但它們是**回報**不是修正，對應的修正落在 `main`、隨 release 抵達。
在 PR/issue 軸重複決定一次沒有意義，也會與 release 審查的結論分岔。

（`trust_root/` 本 fork 沒有，那一批 issue 對本線不適用。）

### 下一步

真正的工作是 **v0.1.8 → v0.1.10 的 358 個 commit 審查**，那是一次獨立的 release 同步，
不是這一輪 ticket triage 的範圍。在那之前每週的 upstream-check 會是紅的——紅燈的意思是
「有一個 release 還沒有人讀」，不是故障。
