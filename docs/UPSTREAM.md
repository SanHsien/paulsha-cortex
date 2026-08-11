# Upstream tracking

最後檢查：2026-08-12

| 欄位 | 值 |
| --- | --- |
| fork | `SanHsien/paulsha-cortex` |
| upstream | `hamanpaul/paulsha-cortex` |
| 前次 review watermark | `b868760`（2026-08-09） |
| 首輪 upstream main | `b79c74aa20e7229c08b279fb0ec062751a8dbeca` |
| 追補 upstream main | `8b34e3e097f4f598b883df0db11669271f83d31f` |
| 前輪 upstream main | `ea76673ab77451fed08a7ff8527f9581cfd2ac6a` |
| 最終 upstream main | `cf791a21f980be1a2e2e5979795a0268880fb248` |
| upstream release | `v0.1.7`（tag object `ab060406e0bf6f7e20a82aaeb835e04b9b239a24`，dereference `cf791a2`） |
| merge 前 origin main | `b354a42d215370ab2d95e05cd879e591ecf58342` |
| 首輪 review 範圍 | watermark 後 104 commits、41 merged PR、0 open PR、1 open issue |
| 本輪增量 | `ea76673..cf791a2`：17 commits、7 merged PR、0 open PR、1 open issue |
| 本輪決策 | 採用 `#457`–`#463` 與 upstream v0.1.7；保留 fork hardening／Windows adapters，並在 fork 修正 Issue `#464` readiness race |

## 2026-08-12 PR review ledger

本輪上游沒有待合併的 open PR。以下 7 個 PR 均已進入 `upstream/main`，合併時的
GitHub checks 無 failed／pending 狀態；本 fork 以 merge 保留 ancestry，並人工解決
CHANGELOG、README、ship cards 與 runtime preflight tests 的重疊。

| 分組 | PR | 決策與理由 |
| --- | --- | --- |
| benchmark／預設值／roster | `#457`、`#458`、`#460` | 採用。補齊成本基線、無 benchmark 的保守預設封套與 11 格 model/persona 候選矩陣。 |
| executor auth gate | `#459` | 採用，並保留 fork 可讀的 YAML 排版與 Windows stdin hardening。此 PR 關閉 Issue `#442` 的 upstream scope。 |
| envelope runtime | `#461`、`#462` | 採用。加入純函式 envelope mapping、schema v3、profile CLI、provenance、inspect models 與對應測試。 |
| release | `#463` | 採用。`VERSION=0.1.7`，annotated tag 可 dereference 到本輪 upstream main。 |

完整 PR 邊界為：`#457`、`#458`、`#459`、`#460`、`#461`、`#462`、`#463`。
下次只評估 `cf791a21f980be1a2e2e5979795a0268880fb248..upstream/main` 與之後
新建／更新的 PR 或 Issue；不要重做本節取捨。

## 2026-08-11 PR review ledger

首輪檢查時上游沒有待合併的 open PR。以下是自前次 watermark 後已進入
`upstream/main` 的 merged PR；本 fork 以 merge 保留 upstream ancestry，並逐一
檢查 30 個與 Windows-first fork 重疊的檔案。合併後 live recheck 新出現的項目另列於下節。

| 分組 | PR | 決策與理由 |
| --- | --- | --- |
| intake、planning、authority、recovery | `#387`、`#388`、`#392`、`#394`、`#398`、`#400`、`#402`、`#403`、`#405`、`#407`、`#409`、`#411`、`#412`、`#413`、`#415`、`#417`、`#419`、`#421`、`#426`、`#428`、`#430`、`#433`、`#436`、`#437`、`#440` | 採用。修正 define/brainstorm failure evidence、artifact authority、orphan rescue、atomic registry、handoff reconciliation、gate provenance 與 auto-claim stalled run。 |
| provider、rate limit、dispatch、delivery | `#423`、`#424`、`#427`、`#429`、`#432`、`#434`、`#435`、`#441` | 採用。補 policy-derived verification、digest、instance-scoped control root、GitHub rate-limit/backoff、provider preflight、spawn admission、typed provider failure 與 executor credential normalization。 |
| adversarial evidence | `#431` | 採用。evidence-claim workflow 強制 adversarial review，直接補強本 fork 的 artifact-backed completion 目標。 |
| packaging／release | `#422`、`#446`、`#451` | 採用程式碼、Python matrix 與 `v0.1.6` 版本狀態；本 fork 仍因 upstream 無 LICENSE 而不發布衍生 wheel／sdist。 |
| monitor concurrency | `#438`、`#444`、`#448` | 採用。移除 process-global `umask` race、修 connection-thread TOCTOU；合併時將修正下沉到共用 Unix/TCP transport，保留 Windows loopback endpoint。 |
| launcher／Issue #442 | `#447` | 部分採用並補強。保留 `cg` zero-tool review/planning 契約，但改由跨平台 typed-argv Python wrapper 傳 stdin，不重新引入 Bash。 |
| continuation design | `#443` | 採用設計與 mid-merge detection MVP；不把設計文件當成完成宣告。 |

完整 PR 邊界為：`#387`、`#388`、`#392`、`#394`、`#398`、`#400`、`#402`、
`#403`、`#405`、`#407`、`#409`、`#411`、`#412`、`#413`、`#415`、`#417`、
`#419`、`#421`、`#422`、`#423`、`#424`、`#426`、`#427`、`#428`、`#429`、
`#430`、`#431`、`#432`、`#433`、`#434`、`#435`、`#436`、`#437`、`#438`、
`#440`、`#441`、`#443`、`#444`、`#446`、`#447`、`#448`、`#450`、`#451`。

## 2026-08-11 post-merge live recheck

| PR／Issue | 決策與理由 |
| --- | --- |
| upstream `#450`／Issue `#449` | 採用到 watermark `8b34e3e097f4f598b883df0db11669271f83d31f`。新增 `retire-delivered`，只有在所有 `pr_refs` 已由 provider 證明 terminal 後才把 orphan run 標為 `superseded`；退休 action 僅在有 last-known-good revision 的 rate-limit degraded 情境容忍舊 authority。fork review 另補 malformed merged timestamp/state fail-closed 與一致 evidence size limit。上游 policy、Python 3.10–3.13、build 與 smoke 全綠。 |
| upstream `#451` | 首次檢查時延後；之後 upstream 於 `ea76673ab77451fed08a7ff8527f9581cfd2ac6a` 合併，並建立可驗證的 `v0.1.6` tag。Python 3.10–3.13、build、smoke 全綠；當時 policy failure 是 tag 建立前的 R-07 時序，fork 以 tag 已存在的 final state 重新驗證後採用。 |

此輪歷史水位已由 2026-08-12 ledger 取代；保留本節供追溯，不重新評估
`#449`、`#450` 或 `#451`。

## Issue ledger

### `hamanpaul/paulsha-cortex#449`，完成

由 upstream `#450` 關閉，本 fork 已採用。`retire-delivered` 不取代或放寬
pre-delivery `abandon`；terminal PR provider evidence、WorkflowRun CAS 與 durable audit
record 仍是退休條件。

### `hamanpaul/paulsha-cortex#442`，完成

- `cg` launcher：已由 upstream `#447` 完成，本 fork 已採用並補 native Windows stdin plumbing。
- `provider:executor` auth gate：本 fork 已在 `openspec-archive` 與 `policy-commit`
  兩張 ship-phase cards 啟用。登入失效時在 remote side effect 前 fail-closed，
  若下一個合法 identity 可用則 reroute；不在所有 build cards 啟用，避免熱路徑
  重複 probe。
- Copilot token deployment：延後。launcher 只會把 process env 既有的 `GH_TOKEN`／
  `GITHUB_TOKEN` 正規化為 `COPILOT_GITHUB_TOKEN`；installer 不從 `gh` keyring
  抽取 token，也不把 secret 寫入 repo。部署者必須用受控 runtime env 提供 token，
  否則 auth gate 會留下 `needs_human`。這是安全邊界，不是未修的程式錯誤。

Issue 已由 upstream `#459` 關閉；下列 deployment 限制仍是 fork 的安全邊界，而非
未處理的 upstream issue。只有在新增非 repo secret store／Windows Credential Manager adapter，
並有 token rotation、ACL、redaction 與 service restart tests 時，才重新評估自動化
Copilot token 佈署。沒有這些證據，不重做「從 keyring 複製 token」探索。

### `hamanpaul/paulsha-cortex#464`，fork 已處理，upstream open

Python 3.13 CI 偶發看到 socket mode `0o755`，不是 #439 的 process-wide umask
復發。`bind()` 會先讓 socket path 可見，Unix transport 隨後才 `chmod(0o600)`；原測試
setup 只輪詢 path existence，因此能在 chmod 前執行 `stat()`。本 fork 改以
`MonitorServer.wait_until_ready()` 作為同步 authority（ready 在 bind／chmod／listen 後
才發布），並保留權限斷言。後續只需檢查 upstream 是否採用等價修正，不重做 umask
hypothesis；Issue 關閉前仍列為待追蹤。

## 同步規則

```powershell
git fetch upstream main --tags --prune
git rev-list --left-right --count origin/main...upstream/main
git log --oneline cf791a21f980be1a2e2e5979795a0268880fb248..upstream/main
gh pr list --repo hamanpaul/paulsha-cortex --state open --limit 50
gh issue list --repo hamanpaul/paulsha-cortex --state open --limit 100
```

逐筆記錄 upstream commit／PR 的採用、部分採用、延後或不採用理由。不要在有
fork-specific Windows adapters 時做無審查的整批 merge。同步後必須跑原生
Windows full gate，Linux CI 則守住 systemd、Bash 與 sandbox 相容面。
