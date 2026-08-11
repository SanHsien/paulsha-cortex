---
status: accepted
work_item: envelope-mapping
---

# envelope-mapping Specification

#454（`#452` 子項）：定案「patchmud ranked 榜 → 封套四欄位」的映射函數與門檻。
本票對票面四個待決各給**一個結論**（不列選項），並落地映射純函式
`paulsha_cortex/coordinator/envelope_mapping.py`（`map_report_to_envelope()`）與
單元測試 `tests/test_envelope_mapping.py`。本票**不接線**任何消費 seam、不改
registry loader／schema、不寫任何檔案——熱路徑與 registry 落地屬 `#452` 實作票。

## 背景（已定案的上游輸入，逐項核對過）

- **patchmud report schema v1**（`patchmud/cli.py` `build_report()`；本票以
  cost-smoke3 八場真 run 實際產出 report.yaml 核對形狀）：頂層
  `schema_version: 1`／`runs_included`／`runs_skipped`／`runs`（per-run 列）／
  `leaderboards`（八榜）。聚合鍵為 `(model, loadout)`；`clear_rate` 榜每列帶
  `model`／`loadout`／`runs`／`clears`（整數）／`value`（浮點）。human run 與非
  `run` mode 場次進 `runs_skipped`，永不入榜。
- **`#453` 已定案**（`docs/superpowers/specs/default-envelope-values-spec.md`）：
  `DEFAULT_ENVELOPE` per-persona 常數——`accepts_bands` 預設 builder/reviewer
  `[green, yellow]`、planner 全值域含 red；`invariant_ceiling` 預設 bypass
  sentinel `null`；`consistency_scope`／`acceptance_modes` 預設全值域；
  `source == "default"` 時既有兩個消費 seam 維持 bypass 字節。
- **`#455` 實測定案**：run 目前一律寫 `pricing_hash=NA`（上游缺口，`cost_per_clear`
  榜整排 NA）；評測指紋為 `(executor, model_id, persona, deck_id,
  deck content_sha256, patchmud version)`，**不含 pricing**；8 關**全跑不抽樣**
  （§4.3：同母題兩變體 clear 結果分歧，變體是獨立訊號）。
- **`#456` 定案**：候選矩陣 N=11；近期可實測**僅 builder 3 格**——pilot-v1 只量
  builder 維度，planner／reviewer 題庫待 `paulsha-patchmud#13`。
- **已知事實**：pilot-v1 的 deck card **沒有 sizing band 標註**（card schema 無此
  欄位）；report v1 的 per-run 列**沒有 encounter 欄位**（只有 `run_id` 命名慣例，
  不可依賴）。

## R1 定案一：v1 只落 `accepts_bands`，其餘三欄誠實維持 `default`（確認票面傾向）

**結論**：映射 v1 只對 `accepts_bands` 產出實測值；`invariant_ceiling`／
`consistency_scope`／`acceptance_modes` 一律回 `#453` 預設值，provenance 逐欄標
`source: "default"` 並附穩定理由碼——這不是「默默略過」，三欄各有明寫的量測缺口：

| 欄位 | 理由碼 | 缺口（issue #454 表列，逐項核對成立） |
|---|---|---|
| `invariant_ceiling` | `not-measurable:no-direct-observable` | pilot-v1 是「修單一 bug」型，invariant 維持數不是刻意設計的變因；從 hidden 測試涵蓋面間接推的代理量效度存疑。真值產房是 `#210` estimator。 |
| `consistency_scope` | `not-measurable:deck-cards-lack-artifact-class-annotation` | 需要 card 標註每關動到的產物類（code/test/spec/…），現行 card schema 無此欄位。 |
| `acceptance_modes` | `not-measurable:deck-acceptance-covers-focused-tests-only` | pilot-v1 驗收一律「public + hidden 測試全綠」，只對應 `focused_tests`；其餘三模式在現有題庫量不到。 |

硬湊三欄等於把不存在的觀測寫成 registry 事實，違反 `#452`「封套欄位只認 patchmud
實測或明示預設兩種 provenance」的邊界；`#453` 已為三欄定了誠實且零行為差的預設，
維持 default 是唯一不發明資料的選項。

## R2 定案二：分數 → band 門檻 = `clear-rate-ladder-v1`（固定門檻、整數算術）

### R2.1 否決「相對排名（report 內分位數）」

1. **單格 report 會退化**：profile run 的現實形狀是一份 report 只有一個
   `(model, loadout)` 群（`#455` 實測 report 即如此），分位數無從計算。
2. **違反評測指紋語意**：相對排名讓某身分的封套值取決於「同榜還有誰」，重評任一
   身分會改變其他身分的 band——與 `#455` §4.1「封套是該身分自己六元指紋的函數」
   直接矛盾，也毀掉跨 report 可比性。
3. 固定門檻對同一份 report 天然可重現，且門檻常數即規則的一部分（見 R2.4）。

### R2.2 未標註 band 的 deck（pilot-v1 現況）：clear-rate 階梯

輸入取 `clear_rate` 榜該群的 `clears`／`runs` 整數對（**不用**浮點 `value`），
比較走整數交叉相乘（`clears × 分母 ≥ runs × 分子`），無浮點邊界誤差：

| 判準（皆含邊界，≥） | 實測 `accepts_bands` |
|---|---|
| `clear_rate ≥ 3/4` | `[green, yellow]` |
| `1/4 ≤ clear_rate < 3/4` | `[green]` |
| `clear_rate < 1/4` | `[]`（不可落 registry，見 R3） |

門檻推導（v1 校準值，錨定 pilot-v1 的 4 母題 × 2 變體結構）：

- **3/4（收 yellow）**：全 deck 8 關容至多 2 關失手。`#455` §4.3 實測同母題兩變體
  clear 分歧（legacy-regression 0/1、state-recovery 0/1），單變體雜訊是真實存在的；
  2 關容忍恰好吸收「一個母題份量」的雜訊，而系統性失守整個母題以上者拿不到 yellow。
- **1/4（收 green）**：至少 2/8＝一個母題份量的通關，是「該身分做得動這類工作」的
  最低證據；低於此線連 green（最小 band）都沒有證據基礎。
- **合理性錨點**：`#455` 實測 haiku 4/8＝0.5 落在 `[green]`——廉價模型吃小工作，
  與成本基準的經濟意圖一致，無荒謬結果。
- red 永不由未標註 deck 的 clear-rate 授予：red 對 builder/reviewer 是死欄位
  （`#453` R1，`#223` 攔截鏈下不可達），本規則實際只需定 green/yellow 分界
  （issue 票面原文）。

**planner red 結構性釘入**：persona 為 planner 且階梯結果非空時，實測
`accepts_bands` 一律併入 `red`（provenance `observation.red_pinned: true`）。red 對
planner 是 `#223` 收斂路徑（`needs_decomposition` 回派 planner 拆分）的**路由必需**，
不是能力實測值，不受門檻管轄；若實測把 planner 的 red 篩掉，`capable()` 落地後
收斂路徑死鎖（`#453` R1 論證）。階梯結果為空（低於 green 地板）時不釘入——該身分
該 persona 已整體不建議落地。v1 此路徑因 pilot-v1 不量 planner 而不可達，但規則
先行定案、實作已含、測試已鎖，避免 planner 題庫落地時憑空再議。

**樣本量判準**：`runs ≥ deck.encounter_count` 才產出實測值（`#455` §4.3 全跑定案；
pilot-v1 為 8），不足者回退 default（理由碼 `incomplete-deck-sample`）。已知限制：
report v1 的 per-run 列無 encounter 欄位，「全覆蓋」無法從 report 本身驗證，本判準
是**必要非充分**條件；補洞需上游 report 增列 per-run encounter id（見 R2.3 前置）。

### R2.3 將來 card 標註 sizing band 後的優先序

deck card 一旦新增 sizing band 標註（值域沿用 `deck/schema.py` `BAND_LEVELS`），
**標註路徑整體取代階梯**（不混用）：band b 的授予判準改為「b 標註關卡子集上的
clear_rate ≥ 3/4」（沿用同一容忍常數），逐 band 獨立評估，並以新 rule id（例如
`banded-clear-rate-v1`）標註 provenance。前置條件（缺一不可，成立前一律走 R2.2
階梯）：(1) card schema 新增 band 標註欄位（patchmud 側 deck 設計，
`paulsha-patchmud#13` 一併考量）；(2) report per-run 列可靠帶出 encounter id，
使 per-band 聚合可從 report dict 純計算——此為上游 report schema 缺口，落地時
應開 patchmud 票。屆時 red 的授予僅對 planner 開放評估（builder/reviewer red
維持死欄位），且 planner red 的結構性釘入優先於任何實測結果。

### R2.4 可重現性契約

門檻常數（3/4、1/4）與樣本量判準都是規則 `clear-rate-ladder-v1` 的一部分；任何
調整 MUST 換新 rule id（`clear-rate-ladder-v2`、…），provenance 的
`observation.band_rule` 記錄所用規則。因此「同一份 report ＋ 同一 rule id →
同一輸出」恆成立（驗收：單元測試斷言重跑 bit-identical，canonical JSON byte-equal）。

## R3 定案三：人工複核閘——**要**（確認建議：函式產 diff 預覽，不自動寫 registry）

**結論**：`map_report_to_envelope()` 只產出「封套值＋逐欄 provenance」的 diff 預覽
payload；registry（版控檔案）的寫入由 `#452` CLI 呈現 diff、經人工確認後 commit。
本票不新增任何寫檔路徑。理由：

1. 自動把一次對局結果寫進版控 registry，等於單次評測直接改變派工行為；`#453` R4
   把 registry diff 設計成「實測進度一眼可辨」（沒寫＝預設、有寫＝實測），這個
   可審計性正是靠「落地即 commit、commit 即有人看」成立。
2. 邊界情況需要人裁決：實測 `accepts_bands` 為空（低於 green 地板）違反 `#209` R2
   「非空」契約，**不得落 registry**——該身分該 persona 是除名還是明示維持
   default，是 roster 決策不是映射決策。輸出以
   `provenance.registry_writable: false` 明確標記（全 default 結果亦標 false：
   `#453` R4 定案 registry 永不寫入預設值，此時無物可落）。
3. 與 `#455` §4.2 不衝突：tick-idle **自動跑評測**（產 report）照舊；本閘管的是
   「report → registry」的落地步，自動評測產出的 proposal 累積待人審，維持
   `#452`「熱路徑只讀值」不變量。

## R4 定案四：映射歸屬 cortex 側（確認票面傾向）

**結論**：純函式住 `paulsha_cortex/coordinator/envelope_mapping.py`；patchmud 維持
輸出領域中立的對局成績，**不認識** cortex 概念。理由：

1. 封套語意（band 值域、persona 集合、`#453` 預設值、`#209` 值域契約）全是 cortex
   側常數；讓 patchmud 輸出 cortex 格式等於把這些常數搬進 patchmud，依賴方向倒置，
   違背 patchmud 對 cortex 零依賴的定位（issue 票面已傾向否決）。
2. 映射是純資料轉換（dict → dict），放 cortex 側不需要 patchmud 任何 runtime——
   模組 MUST NOT `import patchmud`，由測試鎖定（`tests/test_envelope_mapping.py`
   `PurityTests`）。
3. report schema 以 `schema_version` 耦合：本模組僅支援 v1
   （`REPORT_SCHEMA_VERSION_SUPPORTED`），上游升版時 fail-closed 拒絕、不猜測。

## R5 混合 provenance 的 seam 投影規則（承接 `#453` R5 留白）

`#453` R5 只定了「封套全部來自預設」的投影；本票定**逐欄 source** 下的混合規則，
供 `#452` 接線時遵守：

- 投影以**欄為單位**看 source：某 seam 所需欄位中**任一**欄 source 為 `default`，
  該 seam 維持 `#453` R5 的 bypass 字節（`envelope_lookup` 投影回 `None`、
  `capability_lookup` 對該判準回 `None`）；所需欄位**全為** `measured` 時，seam
  才得以實測值作答（`True`／`False`）。
- 推論（v1 決策下的即刻後果）：`envelope_lookup` 兩鍵（`invariant_ceiling`／
  `consistency_scope`）在 R1 下恆為 default → 投影恆回 `None`，plan-review seam
  的 bypass 字節與 v0.1.6 **逐位元不變**。`capability_probe` 的 band 判準只需
  `accepts_bands` 一欄，該欄 measured 落地後即可真答——這是本映射 v1 唯一會（經
  `#452` 接線＋R3 人工閘後）改變派工行為的通道，行為變更範圍被 R1 精確限制在
  band 一個判準上。

## API 契約（實作即規格）

`map_report_to_envelope(report, *, executor, model_id, persona, deck,
patchmud_version, report_model, report_loadout) -> dict`：

- **消費面最小化**：只讀 `report["schema_version"]` 與
  `report["leaderboards"]["clear_rate"]`（`status`／`rows`）；per-run 列、其餘七榜
  一概不碰。`(report_model, report_loadout)` 由呼叫端提供（cortex 身分 ↔ patchmud
  聚合鍵的對應是 profile run 的派工參數，函式不猜測）。
- **deck 識別資訊**：`deck_id`／`content_sha256`／`encounter_count`／
  `measured_personas`（pilot-v1 為 `["builder"]`，出處 `#456`）。
- **fail-closed**（raise `EnvelopeMappingError`）：schema_version 非 1、榜結構缺損
  或 `status != "ok"`、聚合鍵重複列、`clears > runs`、布林混充整數、persona 非法、
  身分字串為空、deck 欄位缺漏。「量不到」**不是**錯誤：persona 維度未量測
  （`persona-dimension-unmeasured`）、身分不在榜上（`identity-not-in-report`）、
  樣本不足（`incomplete-deck-sample`）回退 default 並在 provenance 留理由碼。
- **輸出**：`{"envelope": {四欄}, "provenance": {fingerprint, source, reasons,
  observation, registry_writable}}`——fingerprint 為 `#455` §4.1 六元組（不含
  pricing）；`source` 逐欄 `measured`/`default`；`reasons` 逐欄穩定理由碼；
  `observation` 帶整數 `runs`/`clears` 與 `band_rule`。
- **純函式**：無 I/O、不 mutate 輸入、輸出與 `DEFAULT_ENVELOPE` 常數零 aliasing、
  重跑 bit-identical（皆有測試）。

## 非目標

- 不接線 `claim_readiness.capability_probe`／`planning._plan_review_envelope`、不改
  `model_identities.py`／registry schema、不新增 CLI（`#452` 實作票範圍）。
- 不定 planner／reviewer 題庫（`paulsha-patchmud#13`）、不定 `invariant_ceiling`
  estimator（`#210`）、不動 patchmud 任何一行（上游缺口以開票表達）。
- 本模組的 `DEFAULT_ENVELOPE` 常數為 `#453` R4 定值的唯一落點；`#452` schema v3
  落地查表投影時得整體搬移至 `model_identities.py` 並改 import，不得複製第二份。

## 驗收面（對照 issue #454 驗收逐條）

- 映射為純函式（無 I/O，吃 report dict、吐封套 dict）＋單元測試：
  `paulsha_cortex/coordinator/envelope_mapping.py`＋`tests/test_envelope_mapping.py`。
- 同一份 report 重跑映射結果完全一致：`DeterminismTests`（含 canonical JSON
  byte-equal 與輸入不被 mutate）。
- 量不到的欄位明確標 `default` 而非塞猜測值，且標記在 provenance 可追：
  `DefaultFallbackTests`（逐欄 source＋理由碼斷言）。
- 門檻邊界案例：`ClearRateLadderTests`（3/4、1/4 邊界皆含測試，含非二進位分母的
  整數算術案例 9/12、8/12、3/12、2/12）。
