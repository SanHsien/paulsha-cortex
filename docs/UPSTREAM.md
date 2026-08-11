# Upstream tracking

最後檢查：2026-08-11

| 欄位 | 值 |
| --- | --- |
| fork | `SanHsien/paulsha-cortex` |
| upstream | `hamanpaul/paulsha-cortex` |
| 前次 review watermark | `b868760`（2026-08-09） |
| 本次 upstream main | `b79c74aa20e7229c08b279fb0ec062751a8dbeca` |
| upstream release | `v0.1.5`（tag `efec061fb322ad174a3312c3f5a626e680048856`） |
| merge 前 origin main | `b354a42d215370ab2d95e05cd879e591ecf58342` |
| review 範圍 | watermark 後 104 commits、41 merged PR、0 open PR、1 open issue |
| 本輪決策 | 採用最新 `upstream/main`；衝突逐檔保留 Windows-first adapters |

## 2026-08-11 PR review ledger

上游沒有待合併的 open PR。以下是自前次 watermark 後已進入 `upstream/main` 的
merged PR；本 fork 以 merge 保留 upstream ancestry，並逐一檢查 30 個與
Windows-first fork 重疊的檔案。

| 分組 | PR | 決策與理由 |
| --- | --- | --- |
| intake、planning、authority、recovery | `#387`、`#388`、`#392`、`#394`、`#398`、`#400`、`#402`、`#403`、`#405`、`#407`、`#409`、`#411`、`#412`、`#413`、`#415`、`#417`、`#419`、`#421`、`#426`、`#428`、`#430`、`#433`、`#436`、`#437`、`#440` | 採用。修正 define/brainstorm failure evidence、artifact authority、orphan rescue、atomic registry、handoff reconciliation、gate provenance 與 auto-claim stalled run。 |
| provider、rate limit、dispatch、delivery | `#423`、`#424`、`#427`、`#429`、`#432`、`#434`、`#435`、`#441` | 採用。補 policy-derived verification、digest、instance-scoped control root、GitHub rate-limit/backoff、provider preflight、spawn admission、typed provider failure 與 executor credential normalization。 |
| adversarial evidence | `#431` | 採用。evidence-claim workflow 強制 adversarial review，直接補強本 fork 的 artifact-backed completion 目標。 |
| packaging／release | `#422`、`#446` | 採用程式碼、Python matrix 與 `v0.1.5` 版本狀態；本 fork 仍因 upstream 無 LICENSE 而不發布衍生 wheel／sdist。 |
| monitor concurrency | `#438`、`#444`、`#448` | 採用。移除 process-global `umask` race、修 connection-thread TOCTOU；合併時將修正下沉到共用 Unix/TCP transport，保留 Windows loopback endpoint。 |
| launcher／Issue #442 | `#447` | 部分採用並補強。保留 `cg` zero-tool review/planning 契約，但改由跨平台 typed-argv Python wrapper 傳 stdin，不重新引入 Bash。 |
| continuation design | `#443` | 採用設計與 mid-merge detection MVP；不把設計文件當成完成宣告。 |

完整 PR 邊界為：`#387`、`#388`、`#392`、`#394`、`#398`、`#400`、`#402`、
`#403`、`#405`、`#407`、`#409`、`#411`、`#412`、`#413`、`#415`、`#417`、
`#419`、`#421`、`#422`、`#423`、`#424`、`#426`、`#427`、`#428`、`#429`、
`#430`、`#431`、`#432`、`#433`、`#434`、`#435`、`#436`、`#437`、`#438`、
`#440`、`#441`、`#443`、`#444`、`#446`、`#447`、`#448`。下次只評估
`b79c74aa20e7229c08b279fb0ec062751a8dbeca..upstream/main` 與之後新建／更新的 PR。

## Issue ledger

### `hamanpaul/paulsha-cortex#442`，部分完成，保留 upstream open

- `cg` launcher：已由 upstream `#447` 完成，本 fork 已採用並補 native Windows stdin plumbing。
- `provider:executor` auth gate：本 fork 已在 `openspec-archive` 與 `policy-commit`
  兩張 ship-phase cards 啟用。登入失效時在 remote side effect 前 fail-closed，
  若下一個合法 identity 可用則 reroute；不在所有 build cards 啟用，避免熱路徑
  重複 probe。
- Copilot token deployment：延後。launcher 只會把 process env 既有的 `GH_TOKEN`／
  `GITHUB_TOKEN` 正規化為 `COPILOT_GITHUB_TOKEN`；installer 不從 `gh` keyring
  抽取 token，也不把 secret 寫入 repo。部署者必須用受控 runtime env 提供 token，
  否則 auth gate 會留下 `needs_human`。這是安全邊界，不是未修的程式錯誤。

下次續作條件：只有在新增非 repo secret store／Windows Credential Manager adapter，
並有 token rotation、ACL、redaction 與 service restart tests 時，才重新評估自動化
Copilot token 佈署。沒有這些證據，不重做「從 keyring 複製 token」探索。

## 同步規則

```powershell
git fetch upstream main --tags --prune
git rev-list --left-right --count origin/main...upstream/main
git log --oneline b79c74aa20e7229c08b279fb0ec062751a8dbeca..upstream/main
gh pr list --repo hamanpaul/paulsha-cortex --state open --limit 50
gh issue list --repo hamanpaul/paulsha-cortex --state open --limit 100
```

逐筆記錄 upstream commit／PR 的採用、部分採用、延後或不採用理由。不要在有
fork-specific Windows adapters 時做無審查的整批 merge。同步後必須跑原生
Windows full gate，Linux CI 則守住 systemd、Bash 與 sandbox 相容面。
