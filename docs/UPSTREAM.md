# Upstream tracking

最後檢查：2026-08-22（批次檢視；已審 release 仍為 v0.1.8＝`dc8a968`）

自 2026-08-22 起，`.github/workflows/upstream-check.yml` 每週一 11:00（Asia/Taipei）比對的是**上游的 release
tag**，不是 `main`。`tools/upstream_baseline.json` 的 `track: "release"` 決定這個行為：檢查器問「上游有沒有發出
我們還沒審的 release」，有才失敗並列出該 release 相對 baseline 的 commit。手動執行：
`python tools/check_upstream_updates.py`；要改看每一個 commit 就把 `track` 設成 `"commit"`。

改追 release 的理由記在這裡，不是為了讓紅燈消失：本 fork 至今四次同步（v0.1.5、v0.1.6、v0.1.7、v0.1.8）
全部錨定在上游的 tag，而上游 `main` 每天變動多次。追 `main` 會讓每週檢查永遠是紅的、而且列出的目標在讀到報告
時就已經過期——一個永遠紅的檢查等於沒有檢查。審完把決策寫進本檔，再推進 baseline；先驗證，後推進。

## 2026-08-22 批次檢視：v0.1.8 之後的上游開發中變更

| 欄位 | 值 |
| --- | --- |
| 檢視時上游 `main` | `13366c0`（2026-08-22） |
| 相對 baseline `dc8a968`（v0.1.8） | 202 個 commit、50 個 merged PR、420 個檔案、+123,960／−2,342 行 |
| 上游最新 tag | 仍為 `v0.1.8`（`dc8a968`）——**這批尚未發版** |
| 主要落點 | `tests`（158）、`changelog.d`（142）、`paulsha_cortex/coordinator`（39）、`docs`（30）、`monitor`（12）、`trust_root`（8） |
| 決策 | **不現在同步**，等上游打出下一個 tag 再整批評估 |

理由：這批是上游進行中的開發（trust-root 階段性落地、builder sandbox、event spool、shadow telemetry、
coordinator 重構等仍在連續變動），沒有任何 release 邊界可以錨定；本 fork 相對同一 base 也有 150 個檔案的
Windows-first 改動，在上游收斂前併入等於對移動中的目標做一次會被重做的合併。等 tag 出現後依既有流程逐 PR
評估、記錄決策、再推進 baseline。

| 欄位 | 值 |
| --- | --- |
| fork | `SanHsien/paulsha-cortex` |
| upstream | `hamanpaul/paulsha-cortex` |
| 前次 review watermark | `cf791a21f980be1a2e2e5979795a0268880fb248`（v0.1.7） |
| 首輪 upstream main | `b79c74aa20e7229c08b279fb0ec062751a8dbeca` |
| 追補 upstream main | `8b34e3e097f4f598b883df0db11669271f83d31f` |
| 前輪 upstream main | `ea76673ab77451fed08a7ff8527f9581cfd2ac6a` |
| v0.1.7 upstream main | `cf791a21f980be1a2e2e5979795a0268880fb248` |
| 最終 upstream main | `dc8a968742ce587fba0ec013232a8a9ff1597596` |
| upstream release | `v0.1.8`（tag object `324eb628144bd12173600e18d7638331838a45b6`，dereference `dc8a968`） |
| merge 前 origin main | `b4fe5c7bee7c1651daaf6f07fe4de734b6b66320` |
| 首輪 review 範圍 | watermark 後 104 commits、41 merged PR、0 open PR、1 open issue |
| 前輪增量 | `ea76673..cf791a2`：17 commits、7 merged PR、0 open PR、1 open issue |
| 本輪增量 | `cf791a2..dc8a968`：11 commits、5 merged PR；最新複核為 watermark 後 0 commit、0 open PR、17 open issues |
| 本輪決策 | 採用 `#467`、`#468`、`#470`–`#472` 與 upstream v0.1.8；保留 fork Windows adapters，並在 fork 處理 open Issues `#473`–`#489` |

## 2026-08-12 Issues 476–489 review ledger

檢查時 upstream main 仍為 `dc8a968742ce587fba0ec013232a8a9ff1597596`，沒有新 commit 或 open PR。下列新 issue 均有可重現的 production seam，且修正能維持或加強 fail-closed，因此全數採用；upstream issue 本身仍為 open，不以 fork 完成誤報 upstream closure。

| Issue | 決策與 fork 處置 |
| --- | --- |
| [476](https://github.com/hamanpaul/paulsha-cortex/issues/476) | 採用。service install 在 enable 前以 no-clobber 建立最小 instance-local monitor config，或驗證既有設定；symlink／無效 workspace 直接失敗。 |
| [477](https://github.com/hamanpaul/paulsha-cortex/issues/477) | 採用。dispatch 在 worktree 建立後組 prompt，帶入 resolved authoritative root、base checkout 禁止與 denied path 重新解析指引，不改 sandbox。 |
| [478](https://github.com/hamanpaul/paulsha-cortex/issues/478) | 採用。recovery 使用 production Git seam 移除並重讀 worktree registry；只有未註冊普通目錄才直接清理，任何殘留都 fail-closed。 |
| [479](https://github.com/hamanpaul/paulsha-cortex/issues/479) | 採用。`retry-build` 透傳 initial fanout 同一 identity registry／launcher factory；其他 slice actions 不額外載入 builder identity。 |
| [480](https://github.com/hamanpaul/paulsha-cortex/issues/480) | 採用。Claude safe builder 將 persona tools 映成封閉 `--allowedTools` 規則，只放行 unittest、Edit 與指定 Git read/add/commit 子命令；不含 push/reset/clean 或任意 Bash。 |
| [481](https://github.com/hamanpaul/paulsha-cortex/issues/481) | 採用。只有 slice 當前綁定的 builder/reviewer 可改 current state；recovery 明確清除 binding、Candidate 與 current refs，舊 terminal jobs 僅供 audit。 |
| [482](https://github.com/hamanpaul/paulsha-cortex/issues/482) | 採用。pre-launch absent evidence path 納入 reason＋launch identity 的 canonical request hash，保留 immutable history 並維持同請求冪等。 |
| [483](https://github.com/hamanpaul/paulsha-cortex/issues/483) | 採用。Codex 指定 model 時固定顯式 reasoning effort（預設 medium），只接受 low／medium／high／xhigh，不繼承 ambient max。 |
| [484](https://github.com/hamanpaul/paulsha-cortex/issues/484) | 採用。所有 slice foreign review 共用 `as_review_only()`；Candidate 保持 read-only，verdict 改由受控 terminal JSON 回收，舊注入 launcher 的檔案 verdict 只作相容 fallback。 |
| [485](https://github.com/hamanpaul/paulsha-cortex/issues/485) | 採用。Codex adapter 只容許第一個 content line 的精確 stdin banner；其餘非 JSON、非 object、missing/failed terminal event 仍拒絕。 |
| [486](https://github.com/hamanpaul/paulsha-cortex/issues/486) | 採用。review prompt 直接從 validator 常數列出 category／severity enum，避免 example 與 closed schema 漂移。 |
| [487](https://github.com/hamanpaul/paulsha-cortex/issues/487) | 採用。OAuth auth signal 改採 word boundary，`doc-coauthoring` 不再誤命中，真實 OAuth 訊號維持既有分類。 |
| [488](https://github.com/hamanpaul/paulsha-cortex/issues/488) | 採用只讀可觀測性。status 以 bounded tail、無進展時間、總 runtime 與重複 validation errors 顯示 stale attention；不自動 kill、retry 或改 lifecycle。 |
| [489](https://github.com/hamanpaul/paulsha-cortex/issues/489) | 採用。新增 optional `verification.allowed_paths`；有宣告時與 persona scope 取交集，額外路徑 fail-closed；未宣告的舊 spec evidence 改標 `persona-only`，不誤稱完整 task scope。 |

本節 issue 水位已檢查到 `#489`（含各票截至表列檢查時的最新內容）。下一輪只評估 `dc8a968742ce587fba0ec013232a8a9ff1597596..upstream/main`、新 open PR，以及 `#489` 之後新建或上述 issue 更新後的增量；不要重做本表取捨。

## 2026-08-12 v0.1.8 PR review ledger

本輪上游沒有待合併的 open PR。以下 5 個 PR 均已進入 `upstream/main`；本 fork
以 merge 保留 ancestry，並保留 Windows patchmud shebang adapter 與 native monitor
transport。上游 v0.1.8 annotated tag 已驗證 dereference 到本輪 watermark。

| PR | 決策與理由 |
| --- | --- |
| `#467` | 採用。修正 patchmud report 聚合鍵、agy adapter mapping、deck provenance 指紋與 run evidence 耐久化；fork 保留 Windows PATH 上 Python shebang entry point 的啟動層。 |
| `#468` | 採用。workflow-lane handoff manifest 明確寫入 `workflow_repo`，缺值仍維持 `null`，不推斷歸屬。 |
| `#470` | 採用。以 `wait_until_ready()` 關閉 bind→chmod 測試競態，並採用 upstream 的 slow-chmod deterministic regression；取代 fork 先前的等價修正。 |
| `#471` | 採用。slice spec 顯式 `repo: owner/repo` 貫通 builder／reviewer job、terminal manifest 與 monitor projection；未宣告仍為 `null`。 |
| `#472` | 採用。`VERSION=0.1.8`；release tag object `324eb62` dereference 到 `dc8a968`。 |

完整 PR 邊界為：`#467`、`#468`、`#470`、`#471`、`#472`。Issue `#473`
在 upstream 仍 open；本 fork 本輪先補 deck compile 的顯式 `--repo owner/repo` 傳遞，
不從目錄或 remote 推導。Commit watermark 仍為
`dc8a968742ce587fba0ec013232a8a9ff1597596`；更新後的 issue 水位與下一輪邊界以
上方「Issues 476–489 review ledger」為準。

## 2026-08-12 v0.1.7 PR review ledger

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

### `hamanpaul/paulsha-cortex#464`，完成

Python 3.13 CI 偶發看到 socket mode `0o755`，不是 #439 的 process-wide umask
復發。`bind()` 會先讓 socket path 可見，Unix transport 隨後才 `chmod(0o600)`；原測試
setup 只輪詢 path existence，因此能在 chmod 前執行 `stat()`。Upstream `#470` 已改以
`MonitorServer.wait_until_ready()` 作為同步 authority（ready 在 bind／chmod／listen 後
才發布），並加入 slow-chmod regression；本 fork 已採用，後續不重做 umask hypothesis。

### `hamanpaul/paulsha-cortex#473`，fork 已處理，upstream open

Deck compile 現在接受顯式 `--repo owner/repo`，並把該 work item 已確認的 repo
寫入每一份輸出 slice spec；呼叫端省略時仍輸出 `repo: null`。此修正只傳遞 authority
已有的宣告，不從 repo root 或 Git remote 推導，後續派工、terminal manifest 與
`recent_done` 沿用 `#469` 已驗證的鏈路。後續只比較 upstream 是否落地等價介面與
驗收，不重做 repo inference 方案。

### `hamanpaul/paulsha-cortex#474`，fork 已處理，upstream open

採用 issue 的 DX 問題，但維持既有 fail-closed 與 authority 邊界：

- policy 雞生蛋：新增 `deck compile --policy-from <repo-relative-path>`，讓尚未成為
  canonical `.project-policy.yml` 的候選檔可導出 verification。只接受 repo 內可讀、
  非 symlink 的 YAML mapping；明確指定卻無效時直接失敗，不退回 placeholder。未指定
  候選檔時的 warning 也會說明「先人工落地 policy」與此旗標兩條路徑。
- emit 可見性：成功後列出 resolved absolute output directory 與每個實際寫入檔名。
  唯讀 `cortex ready` 預設沿用 manager specs 目錄；`fanout`／`tick` 的 mutation 入口
  仍要求明確 `--specs-dir`。
- CJK slug：新增 branch-safe `--slug`；task 含非 ASCII 且未指定時警告，不做語意
  transliteration 猜測。
- combo membership：`deck list [combo]` 直接列出 combo 的 cards 與 band-triggered cards；
  不再以全域 card catalog 讓 membership 需要人工反推。現行 `mcu-feature` 的 cards 計數
  與 YAML 已一致，不另造資料修正。
- `repo: null`：沿用 Issue `#473` 的顯式 `--repo owner/repo`，並在省略時新增警告；
  不從 cwd 或 Git remote 推斷 project authority。

後續只比較 upstream 是否落地等價或更嚴格的介面／驗收，不重做上述方案。

### `hamanpaul/paulsha-cortex#475`，fork 已處理，upstream open

採用 issue 揭露的模型身分誤綁風險，並選擇 instance-scoped operator authority，
不在 repo-controlled `model-identities.yaml` 增加任意 executable 欄位：

- `PSC_CLAUDE_EXECUTABLE=/absolute/path/compatible-launcher` 可綁定 Claude
  Code-compatible launcher。只接受絕對、regular、非 symlink 的可執行檔；明確
  override 無效時 fail-closed，絕不 fallback 到 PATH 上的標準 `claude`。
- typed-argv launcher 不展開 interactive alias。未設定 override 時才解析 PATH 上的
  `claude`，並在啟動前把 argv[0] 固定為 resolved path。
- `cortex bootstrap` 與 doctor `review-sandbox` 回報 resolved executable；每個實際
  啟動的 Claude job 將同一路徑保存為 `executable_path`，使 `model_id` 與 provider
  launcher 可共同稽核。
- ship-phase `provider:executor` auth gate 使用同一 resolved executable，override
  與 PATH fallback 的 TTL cache key 都包含該路徑；launcher 變更不會沿用另一個
  `claude` 的登入態而誤擋或誤放行。
- `cortex install service` 會驗證既有 instance／manager env，並可把目前 process env
  的合法 override 寫入該 instance；無效既有值不會在重裝時被掩蓋。

後續只比較 upstream 是否落地等價或更嚴格的 operator authority、fail-closed 驗證
與 provenance；不要改回 alias expansion，也不要把 repo model overlay 變成任意
程式執行入口。

## 同步規則

```powershell
git fetch upstream main --tags --prune
git rev-list --left-right --count origin/main...upstream/main
git log --oneline dc8a968742ce587fba0ec013232a8a9ff1597596..upstream/main
gh pr list --repo hamanpaul/paulsha-cortex --state open --limit 50
gh issue list --repo hamanpaul/paulsha-cortex --state open --limit 100
```

逐筆記錄 upstream commit／PR 的採用、部分採用、延後或不採用理由。不要在有
fork-specific Windows adapters 時做無審查的整批 merge。同步後必須跑原生
Windows full gate，Linux CI 則守住 systemd、Bash 與 sandbox 相容面。

## 2026-08-22：上游 PR、issue、分支的分流規則（一次評估，之後只看增量）

盤點當時上游有 **1 個 open PR、97 個 open issue、274 個分支**。本 fork 以 release tag 為追蹤單位
（`track: "release"`），下面把另外三個面向也定案，之後不必重新推導。

### 分支：`ahead` 不等於「沒合併」

274 個分支中，有 **66 個相對 `upstream/main` 帶著獨佔 commit**。乍看像是「有 66 條沒併回去的
工作」，實際比對三條最舊的（`feature/99-fix-git-runner-cwd`、`feature/100-fix-dispatch-exception-detail`、
`feature/152-fix-mutation-request-timeout`）後發現：**三條的修正都已經在 `main` 裡**，只是上游用
squash merge，squash 出來的 commit 與分支上的原始 commit 不同物件，所以 `rev-list main..branch`
永遠不會歸零。本 fork 也已經有那些測試檔（`tests/test_fix_git_runner_cwd.py` 等）。

其餘 61 條的最後提交集中在 2026-08（`feature/phase2-*`、`feature/718-*` 這類），是上游**正在進行中**
的工作分支——它們的產物會走 PR → `main` → release tag，那才是本 fork 的取用點。

**規則**：不逐條追分支。要判斷某條分支是否真的有未合併的東西，先用主旨或 issue 編號到 `main`
搜一次（`git log --oneline upstream/main --grep="#<編號>"`），有命中就是 squash 假象。

### PR：不逐筆追

上游 PR 走 `main`，合併後即進 release 線；本 fork 的取用點是 tag。當時唯一的 open PR
（[#764](https://github.com/hamanpaul/paulsha-cortex/pull/764) fix-read-repo-tier-fail-closed）
即屬此類，不單獨引用。

### Issue：只追會改變「本 fork 要驗什麼」的

97 個 open issue 幾乎都是上游自己的 work item（`fix(trust-root)`、`fix(planner)`、`fix(gate)`
這種，用 issue 當任務單）。這些是上游的施工中狀態，不是給下游取用的成品。

值得留意但不追的一筆：[#781](https://github.com/hamanpaul/paulsha-cortex/issues/781)
（多 instance 常駐輪詢造成 I/O 放大）——症狀出現在 WSL2/SSHFS，本 fork 是 Windows 原生、
且未啟用多 instance 常駐，暫不適用；若日後本線啟用 daemon 再回頭看。

### 水位

- PR：已看到 **#764**；issue：已看到 **#781**；分支：盤點日 2026-08-22。
- 記在 `tools/upstream_baseline.json` 的 `reviewed_pr_through` / `reviewed_issue_through`。

## 2026-08-23：修正「以 release 為單位」的盲點，並引用一支 fail-closed 修正

前一輪的結論是「本 fork 以 release tag 為取用點，未打 tag 的 202 個 commit 整批等下一個
tag」。**那個結論漏掉一件事**：等 tag 的期間，上游已經修好的 bug 在本 fork 仍然是活的。
判準因此補一條：**上游 `main` 上的修正，只要對照本 fork 程式碼確認「這個缺陷本 fork 也有」，
就不等 tag，直接選擇性移植。**

### 已引用：`59a7a9b` — repo root 解析 fail-closed

- **對照證據**：本 fork 的 `paulsha_cortex/config/paths.py` 仍是
  `_resolve_root("PSC_REPO_ROOT", Path.cwd())`。
- **為什麼本 fork 會痛**：本線以 Windows service 執行，服務的工作目錄正是 operator 的真實
  checkout。於是「解析不出目標 repo」不是失敗，而是把 `git fetch`／`rev-parse`／worktree
  建立打在 operator 的工作區——上游記錄的實網事故就是 `git -C <真 checkout> fetch origin main`。
- **移植範圍**：核心 `configured_repo_root()` / `repo_root(allow_cwd=False)` /
  `RepoRootUnresolvedError` 照抄；五個呼叫端按上游的分類處理（operator 手動 CLI 顯式
  `allow_cwd=True`，daemon 側一律 fail-closed）。**`autonomy` 那段沒有照抄**：上游版依賴本
  fork 還沒有的 `DiagnosticReason`（上游 570／527），改用等價的「沒宣告就走 `.git` 祖先搜尋」。
- **移植時揭露的既有風險**：把 `PSC_REPO_ROOT` 比照 `PSC_AGENTS_ROOT` 指向 per-test 暫存路徑後，
  三個 `recover-pre-candidate` 測試與 `init-sample` 測試立刻失敗——它們以前是在 operator 的
  **真 checkout** 上跑 `git worktree list --porcelain`（再走一步就是 `git worktree remove --force`
  這種寫入動作），並讀真的 `.project-policy.yml`。已改為自備 fixture repo 與最小 policy。
- 驗證：2545 passed / 63 skipped、`tools/dev_check.ps1` 全綠、PR 全部 check 綠。

### 同批掃過但不引用的（逐條看過主旨與檔案）

| commit | 內容 | 結論 |
| --- | --- | --- |
| `6b44624` | `fix(trust-root): job 的 PATH 兩層都補、fail-closed` | 值得，但它改的是 trust-root job 執行面，本 fork 落後 202 個 commit，該區塊已被上游重寫多輪；硬移植等於自行改寫。**觸發條件**：本線實際跑 trust-root job，或該修正隨下一個 tag 進來。 |
| `416da1d` | `fix(coordinator): retry-card evidence 寫入接 resolved_state_path` | 依賴上游 752 系列的 state path 重構，本 fork 沒有那條路徑。 |
| 其餘約 199 筆 | slice-lane、reviewer sandbox、tdd-red、work-item 流程等 coordinator 內部語意 | 屬上游施工中的產品內部；本 fork 的取用點仍是 tag。 |

### 判準（下次照這個做）

1. `git log <baseline>..upstream/main` 過濾 `fix(`，先挑：路徑／編碼／Windows、fail-closed、
   安全性。
2. **對照本 fork 程式碼確認缺陷仍在**（grep 實際的函式，不要只看 commit 訊息）。
3. 確認相依：上游修正若引用本 fork 沒有的模組，就移植其**設計**而不是 diff，並在文件寫明
   哪一段沒照抄、為什麼。
4. 落地後在本檔記下引用的 commit、對照證據與驗證數字。

## 2026-08-23（補）：PR 那一欄只查了 open，補查 `--state all`

上一輪的 PR 盤點寫「當時唯一的 open PR（#764）即屬此類，不單獨引用」。那句話沒錯，但**問錯了
問題**：只查 `--state open` 看不到已關閉的項目。`--state all` 一查，上游有 **400 個 PR**
（394 merged、5 closed、1 open）。

已合併的 394 筆都會變成 `main` 的 commit，落在 commit 稽核範圍（`dc8a968..upstream/main` 的
202 筆已於本輪逐條掃過）。真正只有查 PR 才看得到的是**未合併就關閉**的 5 筆：

| PR | 實查結果 |
| --- | --- |
| #787 `chore(deps): 讓 codeql-action 的升版走同一個 PR` | **不是上游的變更**：本 fork 端誤開到上游後立刻關閉的那一個（見 `docs/FORK.md` 的「只對本 fork 開 PR」）。 |
| #239／#236／#233 `feat(coordinator/work_actions): retry 分類` | **已被上游自己取代**：同主題由 PR #240（`feature/216-retry-invalidation`）合併進 `main`，`git log upstream/main --grep="retry 分類"` 命中 `ec68e4c`。內容已在 commit 稽核範圍內。 |
| #171 `feat(workflow): 完成 release-pipeline` | **已被上游自己取代**：由 PR #174（`feature/95-release-pipeline-land`）合併，`9820327`／`45f2d94` 可查。 |

**結論：5 筆都不需要動作**，但這是查過之後的結論。

### 水位

- PR：**#787**（`reviewed_pr_through` 764 → 787）
- issue：仍是 **#781**
- commit：仍是 `dc8a968`（追蹤單位為 release tag，選擇性移植的判準見本檔前段）

**判準補一條**：PR 與 issue 一律用 `--state all` 查。未合併就關閉的 PR 永遠不會出現在 commit
清單裡，而那正是「上游拒收、但可能對本 fork 有價值」的那一類。
