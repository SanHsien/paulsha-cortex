# 評測成本基準實測（benchmark cost baseline）

> Issue：#455（#452 子項）。本文件落地「跑一次 profile 要花多少」的實測數字，
> 並據此定案 pricing snapshot 處置、補評測排程位置與重評觸發條件。

## 1. 實測設定

| 項目 | 值 |
|---|---|
| deck | `decks/pilot-v1`（8 關 = 4 母題 × 2 變體） |
| 模型 | `haiku` → `anthropic:claude-haiku-4-5`（Anthropic HTTP API，OAuth bearer） |
| loadout | `P0T0R0`（SOLO，patchmud run 預設） |
| patchmud | v0.0.1 @ `abdf808`（`$HOME/prj_pri/paulsha-patchmud`） |
| 執行方式 | `patchmud run <encounter> --model haiku`，8 關依序執行、不並行 |
| 計價 | pricing snapshot `2026-08-11`（haiku 牌價：input $1.00 / cache read $0.10 / output $5.00 per MTok；**假定值**：取自 Anthropic 官方定價頁牌價，模型知識截止 2026-01，未能於實測當日線上複驗） |
| 計費規則 | 照 `patchmud.ledger.cost.entry_cost`（billed totals、Decimal 累加）自 `ledger.jsonl` 重算 |

原始 run 封存留在 `$HOME/prj_pri/paulsha-patchmud/runs/cost-smoke3-*`（不進版控）。

備註：首選 `sonnet` 於煙霧測試連續兩次 HTTP 429（rate_limit_error；當時同帳號另有並行
agent 工作），改用 `haiku` 後 8 關一次全過、零重試。這個 429 樣本本身就是
「補評測與正常派工搶配額」的直接證據，見 §4.2。

## 2. 實測成本表（per-encounter 與全 deck）

tokens 為 API 回報的 billed totals（cached 全程為 0——patchmud adapter 未啟用
prompt caching）；`model_wall` 為 ledger 逐回合 `wall_clock_ms` 合計（純模型延遲）；
`process_wall` 為整個 `patchmud run` 行程的牆鐘時間（含 sandbox probe 執行）。

| encounter | turns | billed input | billed output | model_wall (s) | process_wall (s) | USD | clear |
|---|---:|---:|---:|---:|---:|---:|---:|
| input-validation-v1 | 6 | 8,967 | 827 | 13.1 | 14 | 0.0131 | 0 |
| input-validation-v2 | 6 | 9,383 | 902 | 14.5 | 16 | 0.0139 | 0 |
| legacy-regression-v1 | 7 | 12,410 | 1,270 | 18.3 | 18 | 0.0188 | 0 |
| legacy-regression-v2 | 5 | 6,564 | 440 | 9.9 | 11 | 0.0088 | 1 |
| parser-edge-v1 | 5 | 6,512 | 420 | 10.0 | 10 | 0.0086 | 1 |
| parser-edge-v2 | 6 | 8,660 | 729 | 14.1 | 16 | 0.0123 | 1 |
| state-recovery-v1 | 8 | 16,020 | 1,303 | 17.4 | 17 | 0.0225 | 0 |
| state-recovery-v2 | 7 | 11,844 | 803 | 14.4 | 16 | 0.0159 | 1 |
| **全 deck 合計** | **50** | **80,360** | **6,694** | **111.8** | **≈118** | **0.1138** | **4/8** |

交叉驗證：`patchmud report --runs "runs/cost-smoke3-*" --pricing <snapshot>` 收得
`runs_included=8`、clear_rate 0.5、power 65.59；但 `cost_per_clear` 榜為 NA，原因見 §4.1。

## 3. 外推：N 個身分全量 profile 的預算上界

單一身分 × 全 deck 的實測錨點：**≈ 8 萬 input + 0.67 萬 output tokens、
牆鐘 ≈ 2 分鐘、haiku 計價 ≈ $0.11**。

以「token 用量與 haiku 實測同量級」為假設（不同模型話癆程度不同，此為一階近似），
按各級距牌價換算單身分全 deck 成本：

| 模型級距（假定牌價 in/out per MTok） | 單身分全 deck USD |
|---|---:|
| haiku 級（$1 / $5，實測） | $0.114 |
| sonnet 級（$3 / $15） | ≈ $0.34 |
| opus 級（$15 / $75） | ≈ $1.71 |

N＝**11**（`#456` R7 定案，(executor, model_id, persona) 粒度：15 格 − 硬約束排除
4 格；每格＝一次完整 deck run）。其中**近期可實測僅 builder 3 格**——pilot-v1 目前
只量 builder 維度（planner／reviewer 題庫待 `paulsha-patchmud#13`），其餘 8 格待
題庫落地。非 Anthropic 身分（codex／agy／cg）走各自 CLI 訂閱登入態，無逐 token
帳單，USD 記 0 但仍吃該家配額：

| 情境 | 近期可實測（builder 3 格） | 全量上界（11 格） |
|---|---:|---:|
| 全數 haiku 級 | ≈ $0.34 | ≈ $1.3 |
| 全數 sonnet 級 | ≈ $1.0 | ≈ $3.7 |
| **上界：全數 opus 級** | ≈ $5.1 | **≈ $18.8** |

牆鐘：haiku 實測 2 分鐘／deck；保守放大 3–5 倍給慢模型，單格 ≤ 10 分鐘、
11 格依序全跑 ≤ 110 分鐘。planner／reviewer 專用 deck 規模未知，上表以
「與 pilot-v1 同規模」為一階假設。若 `#456` R4 待確認身分全數登錄
（`gemini-3.6-flash-high` +1、`gpt-5.4-codex` +3 → N=15），opus 級上界
≈ **$26**；兩票數字須同步更新（`#456` R7 分期註記）。

結論：**美元成本不是「一次性」語意的主要約束（上界 $19 起、極端 $26），
真正的稀缺資源是限流配額與牆鐘**——sonnet 煙霧測試的連續 429 證明評測流量
與並行派工互撞是現實風險，這直接決定 §4.2 的排程定案。

## 4. 三項定案

### 4.1 pricing snapshot 不納入 #452 評測指紋（定案：不納入）

**結論**：評測指紋維持 `(executor, model_id, persona, deck_id, deck content_sha256,
patchmud version)`，**不加入 pricing snapshot**；pricing 調價**不**觸發重評。

理由：

1. 指紋守護的是**能力觀測**的有效性（clear rate、power、token 用量）。這些觀測
   事實與單價完全正交——調價不會讓已量到的 token 數失效。把 pricing 入指紋，
   等於每次調價就把全部身分打回未評測、重燒真模型配額，恰好摧毀「評測很貴
   所以一次性」的初衷。
2. 成本可比性是**報表層**性質：billing facts（token 數）永久有效，USD 在
   `patchmud report --pricing <snapshot>` 時重算，「同一張榜用同一份 snapshot」
   即可比。patchmud 的設計也正是如此（run.yaml pin snapshot content hash、
   價格改動不影響已封存 run）。
3. cortex 側落 `model-identities.yaml` 的封套欄位（accepts_bands 等）不含 USD；
   provenance 記 deck 與 run 出處即可回溯任一時點的成本。

**實測揭露的上游缺口**：`patchmud run` 目前一律寫 `pricing_hash: NA`（CLI 無
`--pricing` 參數可在 run 時 pin），導致 `report --pricing` 對這些 run 拒絕計價、
`cost_per_clear` 榜整排 NA（skip 理由：「run 未 pin pricing snapshot」）。本表 USD
是照 `entry_cost` 規則從 `ledger.jsonl` 重算的。應在 paulsha-patchmud 開票補
`patchmud run --pricing <snapshot>` pin 路徑；此缺口不影響本定案方向。

### 4.2 補評測排程：periodic tick 只在 idle 時補，單次至多一個身分（定案：tick-idle，非一律手動）

**結論**：補評測掛 periodic tick，但加兩道閘：**只在 idle**（無 active dispatch／
claim 進行中）時啟動；**一次 tick 至多補一個身分**（全 deck 依序、不並行）。
另保留明確 CLI（`cortex model profile`）作手動路徑與 `--force` 入口。

理由：

1. 成本面已被實測排除：單身分 2 分鐘、$0.11–$1.71，掛 tick 完全負擔得起，
   「一律手動」會讓 default-envelope 身分長期停在保守預設，白白放棄實測值。
2. 配額面是真風險：sonnet 煙霧測試在同帳號有並行 agent 工作時連兩次 429。
   idle 閘 + 單身分節流正對此病：評測流量只在派工空檔出現，且量被限制在
   一個 deck（≈50 次 API 呼叫）內。
3. 評測 runner 需具 429 退避重試（本次實測 runner 為指數退避、上限 8 次），
   且失敗放棄後不留半套側寫——維持 #452 的「熱路徑只讀值」不變量。

### 4.3 重評觸發條件維持 #452 原案，不需修正（定案：確認，含一處明確排除）

**結論**：重評觸發維持 #452 D 節原清單——新增身分、`model_id` 變更、deck 內容
pin 變更、明確 `--force`——**不加嚴、不放寬**；並明確補一條排除：**pricing 調價
不觸發重評**（呼應 4.1）。

理由：單次評測的實測成本（分鐘級、單身分 ≤ $1.71）低到不需要更嚴的觸發門檻；
反向亦然——沒有任何觀測支持「定期重評」之類更寬的觸發（模型能力漂移應由
`model_id` 版本變更表達，同一 model_id 視為同一能力）。

**附帶定案（issue「抽樣或全跑」）**：8 關**全跑**。抽 4 母題各 1 變體只省
≈ $0.05（haiku）／≈ $0.9（opus 級），卻放棄變體對過擬合的偵測能力；本次實測
同母題兩變體 clear 結果分歧（input-validation 0/0 但 legacy-regression 0/1、
state-recovery 0/1），證明變體確實提供獨立訊號，不可抽掉。

## 5. 已知限制

- 單一模型（haiku）單次樣本；不同模型的 token 用量與回合數會漂移，外推表
  是一階近似。#456 定案身分矩陣後，各格子的實測值以該身分自己的 profile run 為準。
- pricing snapshot 單價為牌價假定值（見 §1），未含任何折扣／快取優化；
  cached tokens 全程為 0，若 patchmud adapter 未來啟用 prompt caching，
  sonnet／opus 級成本會再降。
- pilot-v1 只覆蓋 builder 維度；planner／reviewer 的成本要等
  `paulsha-patchmud#13` 題庫落地後才能實測。

## 勘誤追記（2026-08-12，cortex#466）

- **§4.3「同母題兩變體 clear 分歧證明變體提供獨立訊號」的證據不成立**：
  paulsha-patchmud#21 的盤點顯示，本次實測 haiku 的 4 場失敗（含 input-validation
  兩變體全敗）全是 unified diff 解析失敗（`production_loc: 0`），分歧反映的是
  逐場的協定格式雜訊，不是變體設計出的獨立能力訊號。「8 關全跑」的定案維持
  （成本差可忽略、變體對過擬合的偵測能力仍是真需求），但不得再引用本段當
  變體有效性的實證。
- **成本外推不受影響**：§2 的 token／wall-time／USD 是 billing facts，與失敗
  原因無關。惟「haiku 4/8」不可再被引用為能力分佈的證據（同見
  `envelope-mapping-spec.md` 勘誤追記）。
- patchmud 已於 PR #15（08-12，本文件實測之後）落地 codex／agy OAuth headless
  adapter：§3「近期可實測僅 builder 3 格」的前提改變，agy／codex 身分的 builder
  格已可實測（效力範圍：effort 硬編 high 的檔位）；格數以 `#456` 矩陣的最新
  狀態為準。
