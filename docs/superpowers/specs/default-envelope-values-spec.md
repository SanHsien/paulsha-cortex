---
status: accepted
work_item: default-envelope-values
---

# default-envelope-values Specification

#453（`#452` 子項）：定案「某身分尚無 patchmud 實測 benchmark 時，封套四欄位
（`accepts_bands`／`invariant_ceiling`／`consistency_scope`／`acceptance_modes`，值域契約
見 `#209` R2，`docs/superpowers/specs/design-model-capability-envelope-spec.md:105-121`）
填什麼」。本票是設計文件，不實作、不改任何 `.py`；每一欄給**一個定案值**與可追溯推導，
不列選項。判準只有兩條（`#453` 驗收原文）：套用預設後 claim → plan → build → review 的
決策與 v0.1.6 **逐位元相同**，且不誤傷任何現行可派工身分。

## 背景（main @ `ea76673`，v0.1.6，逐一實測核對）

- **消費端 seam 現況全 bypass**：`claim_readiness.py:421-440` 的 `capability_probe()` 在無
  lookup provider 時一律 `_passed("capability", bypass="envelope_unavailable")`；
  `planning.py:470-526` 的 `_plan_review_envelope()` 在 `envelope_lookup` 為 `None` 或回傳
  `None` 時回 `observation={"bypass": "envelope_unavailable"}` 通過；`manager.py:6710` 現況
  固定傳 `envelope_lookup=None`。「逐位元相同」的基準線就是這組 bypass 字節。
- **red band 在 build 之前就被攔截**（`#223`）：`claim.py:1244-1270`（`decomposition_route()`、
  `DECOMPOSITION_DEPTH_LIMIT = 2`）定義收斂路徑；`manager.py:6807-6829` 在 plan 相位最後一格
  pending 檢查點對 `sizing_band == "red"` 路由 `needs_decomposition`／`needs_human`，build 不會
  收到 red run。band 門檻本身在 `claim.py:1227-1242`（Green ≤3／Yellow ≤6／Red >6，字串沿用
  `deck/schema.py:57` `BAND_LEVELS`）。
- **`invariant_ceiling` 的歷史分布不存在**：`#210` spec
  （`docs/superpowers/specs/sizing-envelope-calibration-spec.md:116-139`）已查證
  `invariant_count` 從未被 `CompletionRecord` 持久化；本票補充查證——runtime evidence root
  （`$PSC_AGENTS_ROOT/coordinator/`）grep `invariant_count` 命中 0 個檔案、repo 內
  `docs/superpowers/plans/*.md` frontmatter 宣告 0 筆，唯一出現具體值的是測試 fixture
  （`tests/test_planning_review_gate.py`：1／2／5／99）。「取歷史最大值 + 餘裕」的資料前提
  **不成立**。
- **`#452` §B 已定的邊界**：封套欄位「一律有值」是為了讓 `#209` R2「`accepts_bands` 缺省
  MUST 拒載」永不觸發；同段明文「**其餘三欄的缺省語意仍照 `#209` 定的 bypass 處理**」。
  即：只有 `accepts_bands` 必須有具體集合值，另外三欄允許以 bypass 語意作為預設。
- **registry 現況**：packaged registry（`paulsha_cortex/coordinator/data/model-identities.yaml`）
  只有 1 個身分（`agy`/`gemini-3.1-pro-high`/`capabilities: [planning]`）；loader
  （`model_identities.py:15-16` schema {1,2}、`:110-152` fail-closed 白名單）尚無封套欄位。
  模型鏈三段 persona 固定為 `workflow.py:23` `MODEL_CHAIN_PERSONAS = {planner, builder, reviewer}`。

## Goals

- 對四欄位各定案一個預設值，每個值的推導可追到既有 gate 或已查證的資料事實（`#453` 驗收：
  不得是「看起來安全」的拍腦袋數字）。
- 定案預設值的存放機制（`DEFAULT_ENVELOPE` 常數 vs 寫進 registry 每列）。
- 給出 `#452` 實作時必須照做的 bit-identical 回歸測試規格。

## Requirements

### R1 `accepts_bands` 預設：builder `[green, yellow]`／planner `[green, yellow, red]`／reviewer `[green, yellow]`

預設值依 persona 而異（此事實同時決定了 R4 的存放機制）：

| persona | 預設 `accepts_bands` | 推導 |
|---|---|---|
| builder | `[green, yellow]` | `#223` 把 red 攔在 build 之前（`manager.py:6807-6829`；`claim.py:1244-1270`）；ship repair 對 red 是防禦性 `ValueError`（`delivery.py:46-68` `repair_budget_for_band`）。red 到不了 build，寫入即死欄位；砍掉 red 不觸及任何現行可達路徑。 |
| planner | `[green, yellow, red]`（全值域） | red 的收斂路徑就是 `needs_decomposition` 回派 planner 拆分（`claim.py:1247` 註解原文；`#223` 驗收條件 4）。planner 預設不含 red 會讓 `#223` 的收斂路徑在 `capable()` 落地後死鎖。green/yellow 則是 planning 的本業（band 本身由 plan 產物算出，`planning.py:651-720` `compute_sizing_score` 需要 `kind='plan'` artifact——planning 在 band 存在之前就發生）。 |
| reviewer | `[green, yellow]` | 見下方查證。 |

**reviewer 含不含 red 的查證結論**（`#453` 票面待定項）：red 不可能以 red 身分抵達 review，
論證三段——

1. red 在 plan 相位最後一格 pending 檢查點就被路由走（`manager.py:6807-6829`），該 run 不會
   進 build，因此也不會有 build candidate 進 review；
2. 拆分後的子 work item 是**新的 run**（`decomposition_depth + 1`），從 plan 相位重新走，band
   由子 run 自己的 plan 重算——若仍 red 會被同一檢查點再攔（至 `DECOMPOSITION_DEPTH_LIMIT = 2`
   逾限轉 `needs_human`，`claim.py:1253-1270`）；能走到 review 的子 run 必然 green/yellow，
   review 用的是子 run 自己的 band，不繼承父 run 的 red；
3. 殘餘路徑也封死：resume 掃描對 `needs_decomposition` run 原樣浮現、不得以原身分續跑
   （`claim.py:1126-1137`）；yellow plan review 分支只處理 yellow（`manager.py:6832-6852`，
   red 已在其前被攔）。

因此 reviewer 的 red 與 builder 同理是死值；寫入會讓 registry 宣稱「reviewer 收 red」而管線
永不路由 red 至 review，誤導可觀測性。定案 `[green, yellow]`。

### R2 `invariant_ceiling` 預設：走 bypass 例外（sentinel `null`），不取數

本欄**不定有限數值**，預設為明確的 bypass sentinel（YAML `null`／Python `None`），語意沿用
`#209` R2 第二列既有缺省契約：「缺省 SHALL 視為 capability 檢查 bypass（比照
`claim_readiness.capability_probe` 現行 `envelope_unavailable` 語意），MUST NOT 視為 `0`」。
loader 與查表投影 MUST NOT 把 `null` 讀成 `0`。理由四條，逐條可追溯：

1. **值域無界，不存在「最保守有限值」**：`invariant_count` 值域為 `≥ 0` 整數、無上限
   （`planning.py:475-477` 只驗 `>= 0`）。任何有限 `N` 對宣告 `invariant_count = N + 1` 的
   plan 都構成今天不存在的過濾（今天 bypass 放行、套預設後 `envelope-exceeded` 判否，
   `planning.py:506-518`），直接違反「逐位元相同」驗收。R3 的兩個 list 欄位值域是**封閉有限
   集**、上確界存在且可寫出——這個結構性不對稱正是本欄單獨開例外、而 list 欄位不開的理由。
2. **歷史分布不存在，任何數字都是拍腦袋**：`#210` spec R3 已查證 `invariant_count` 從未持久化
   （`sizing-envelope-calibration-spec.md:116-139`）；本票補充查證 runtime evidence root 0 檔案
   命中、repo 內 plans frontmatter 0 宣告（見背景）。「歷史最大值 + 餘裕」無資料可依，任何
   具體數字都違反 `#453` 驗收「每一欄的預設值有明寫的推導依據」。
3. **既有契約已為此欄預留 bypass 語意，走 bypass 是沿用而非修訂**：`#209` R2 第二列（上引）
   ＋ `#452` §B 明文「其餘三欄的缺省語意仍照 `#209` 定的 bypass 處理」。
4. **真值另有指定產房**：`#210` 把 `calibration_source`／`calibrated_at` 只掛在本欄（`#210`
   spec R1），estimator（通過率曲線）是本欄數值的指定來源，且樣本 `< 3` 時明文保留預設
   （`sizing-envelope-calibration-spec.md:178`）。estimator（或 patchmud 實測）落地前，
   「尚無資料、不過濾」就是本欄唯一誠實的值。

### R3 `consistency_scope`／`acceptance_modes` 預設：取全值域

- `consistency_scope` 預設 = `[code, test, spec, openspec, changelog, docs, pr, issue]`
  （`#209` R2 值域全集）。
- `acceptance_modes` 預設 = `[focused_tests, repo_gate, live_evidence, github_closure]`
  （`#209` R2 值域全集）。

**「等同現況 vs 可觀測性」取捨結論**：取全值域，理由——

1. **可行性（與 R2 的對比）**：兩欄值域是封閉有限集，「全值域」是存在且可寫出的最保守值
   （集合包含判準的上確界）；不必像 `invariant_ceiling` 那樣被迫用 sentinel。
2. **等同現況**：`acceptance_modes` 的工作側對應值 `acceptance_mode` 至今不存在於任何 `.py`
   （本票重跑 `#209` 驗收 grep：四欄位名在 `paulsha_cortex/`／`tests/` 零命中，仍成立），該
   判準今天不可能被評估；其工作側落地時值域必受 R2 四值 fail-closed 約束（`#209` R8），全值域
   預設在該 seam 恆真。`consistency_scope` 的既有消費 seam（`_plan_review_envelope` 的
   `artifact_classes` 鍵）由 R5 的投影規則保證維持 bypass 字節，不經全值域比對（見下方注意）。
3. **可觀測性**：全值域是「寫得出來的值」——`cortex doctor`／`inspect` 可顯示欄位值＋
   `profile_provenance.source == "default"`（`#452` 驗收 1）；`#454` 實測值落地時，registry
   資料層的 diff（全值域 → 實測子集）直接可見，schema 形狀不變。bypass sentinel 版本則什麼
   都顯示不出來，且 `#454` 換值時要同時改形狀。「可觀測性有意義」不靠預設值過濾（預設期
   本來就該零過濾），靠的是值與來源在資料層一眼可辨。

**注意（normative，交辦 `#452`／後續 judge 票）**：plan frontmatter 的 `artifact_classes`
現行只驗「非空字串列表」、**不約束值域**（`planning.py:478-485`；
`tests/test_planning_review_gate.py:156` 有域外值 `exotic` 的既有測試）。因此「全值域
`consistency_scope`」對域外 artifact class 的集合包含判準會判否，**不是**無條件恆真。實作
`capable()` 判準 3 時，對 `source == "default"` 的封套 MUST 對域外 artifact class 走可觀測
bypass（或先把工作側值域收斂到 R2 全集），MUST NOT 讓預設封套產生比現況更嚴的過濾。在 R5 的
投影規則下，此邊界情況不會出現在既有 plan-review seam。

### R4 存放機制：`DEFAULT_ENVELOPE` per-persona 常數，查表投影時套用；registry 檔案永不寫入預設值

定案 **`DEFAULT_ENVELOPE` 常數**（落點 `model_identities.py`，隨 `#452` schema v3 落地），
形狀為 per-persona 表（key 沿用 `workflow.py:23` `MODEL_CHAIN_PERSONAS`）：

```python
# 示意（#452 實作票落地；本票只定值與形狀）
DEFAULT_ENVELOPE: Mapping[str, Mapping[str, object]] = {
    "planner":  {"accepts_bands": ["green", "yellow", "red"], "invariant_ceiling": None,
                 "consistency_scope": [...全值域...], "acceptance_modes": [...全值域...]},
    "builder":  {"accepts_bands": ["green", "yellow"], "invariant_ceiling": None, ...},
    "reviewer": {"accepts_bands": ["green", "yellow"], "invariant_ceiling": None, ...},
}
```

套用點在**載入後的查表投影**：查表 API 在 `(executor, model_id, persona)` 語境下，該身分
無實測封套時回傳 `DEFAULT_ENVELOPE[persona]` 並標 `profile_provenance.source = "default"`。
「寫進 registry 每列」方案否決，理由：

1. **per-persona 預設無法攤平成每列單值**：R1 的 `accepts_bands` 依 persona 而異（red 對
   planner 是必含、對 builder/reviewer 是死值），而 `#209` R2 把欄位掛在 `(executor, model_id)`
   複合鍵上；一個身分可同時具多個 capability（`model_identities.py` `capabilities` 為 list），
   攤平寫入每列必然失真或被迫全取聯集（等於 builder 也收 red，回到誤導可觀測性）。
2. **資料層一眼可辨**（`#452` §B 待決項原文的訴求）：檔案裡「沒寫」＝用預設、「有寫」＝實測
   （或人工覆寫），registry diff 直接反映實測進度；預設展開進每列後，這個區別只剩 provenance
   欄位可辨，且 `#454` 每次換算都要逐列改檔。
3. **向後相容零遷移**：v1/v2 檔案與 host-local overlay（`$PSC_PROJECT_CONFIG_ROOT` 疊加）
   載入後自動獲得預設投影，不需 migration，直接滿足 `#452` 驗收 5。
4. **單一真值**：改預設只改一處常數；寫進每列則 N 列同步改、會漂移（比照 `claim.py:1225`
   「三處共用純函式避免各自硬編碼門檻」的既有慣例）。
5. **`#209` R2 拒載規則不需修訂**：「一律有值」在查表投影層成立——任何 `(identity, persona)`
   查表必回一份完整封套（實測或預設），`accepts_bands` 永遠是非空 list，「缺省 MUST 拒載」
   永不觸發；`invariant_ceiling` 的 `None` 是 R2 已定義語意的明確 sentinel，不是缺欄位。

### R5 證據層規則：`source == "default"` 在既有決策證據 surface 上維持 bypass 字節

`#453` 驗收的「逐位元相同」落在既有兩個消費 seam 的證據字節上，`#452` 實作 MUST 遵守：

- **`capability_lookup` seam**（`claim_readiness.capability_probe`）：對封套全部來自預設
  （`source == "default"`）的身分，provider MUST 回傳 `None`（**不是** `True`）——使
  `capability` 格維持 `_passed("capability", bypass="envelope_unavailable")`，與 v0.1.6 的
  observation 逐位元相同。`True`／`False` 保留給實測側寫。
- **`envelope_lookup` seam**（`planning._plan_review_envelope`，`#209` R7 兩鍵 Mapping）：
  投影所需兩鍵之任一來源為預設（`invariant_ceiling` 為 `None`，或 `consistency_scope` 為
  default）時，投影 MUST 回傳 `None`——使 envelope 檢查維持
  `observation={"bypass": "envelope_unavailable"}` 字節。實測值與預設值混合時如何投影屬
  `#454` 範圍，本票不定。

預設值的可觀測性一律走**新增的讀取面**（`cortex doctor`／`inspect`／profile 顯示，`#452`
驗收 1），MUST NOT 藉由改寫既有決策證據來達成。R1 的預設值被 R6-T2 證明在全部可達輸入上
恆不排除，因此本規則不是「用 bypass 掩蓋會誤傷的預設」，而是把「零行為差」從論證升級為
字節等式。

### R6 bit-identical 回歸測試規格（`#452` 實作 MUST 照做）

**「決策」的精確定義**：以下五個純函式層 surface 的輸出——
`evaluate_pre_claim_readiness` 的 `ReadinessOutcome`（含每格 name／passed／
terminal-retryable 分類／observation）、`plan_review_gate` 的 `PlanReviewOutcome`（含
failed_check 與各 check observation）、`sizing_band()` + `decomposition_route()` 的路由結果、
`repair_budget_for_band()` 的預算值或例外、`validate_completion_record()` 的 normalized
輸出或例外。比對方式：canonical JSON 序列化（`json.dumps(..., sort_keys=True)`）後
**byte-equal**。`cortex doctor`／`inspect` 顯示層與新增 provenance 讀取面明確排除在比對外
（它們不是決策）。

- **T1 golden 雙配置決策軌跡**：同一 fixture corpus 跑兩遍——baseline 配置
  （`capability_lookup=None`、`envelope_lookup=None`，即 v0.1.6 語意）vs 預設封套配置
  （provider 由 packaged registry + `DEFAULT_ENVELOPE` 建構）——逐 case 斷言五個 surface
  序列化字節相等。corpus 最低覆蓋：plan `invariant_count ∈ {0, 1, 99}`；`artifact_classes`
  含域內與域外值（沿用既有 `exotic` fixture）；band green/yellow/red 三帶；
  `decomposition_depth ∈ {0, 1, 2}`；registry 全體身分 × 三 persona；readiness 六格全序
  （`claim_readiness.py:57` `CHECK_ORDER`）。
- **T2 `DEFAULT_ENVELOPE` 恆不排除 property test**：不經 R5 的 bypass 規則、**直接**以集合／
  比較語意評估 R1–R3 的預設值對 corpus 內全部可達 `(work, identity, persona)` 組合，斷言
  無一被排除（可達＝依 `#223` 攔截鏈可抵達該 persona 的輸入：builder/reviewer 只餵
  green/yellow，planner 三帶全餵）。此測試是 RED 可證的：變異任一預設值（如 builder
  `accepts_bands` 改 `[green]`）必須讓它轉紅——T1 守 seam 字節、T2 守預設值本身，兩者缺一
  不可。
- **T3 loader／相容性**：v1/v2 registry 檔案照常載入（`#452` 驗收 5）；查表投影對無實測
  身分回 `DEFAULT_ENVELOPE[persona]` 且 `profile_provenance.source == "default"`；
  `invariant_ceiling=None` 不被讀成 `0`（斷言不觸發 `envelope-exceeded`）；host-local
  overlay 身分同樣獲得預設投影。

## 非目標

- 不實作任何程式碼：`grep -rn "accepts_bands\|invariant_ceiling\|consistency_scope\|acceptance_modes"
  paulsha_cortex/ tests/` 在本票合入後仍須零命中（`#209` 驗收面既有條款，本票維持）。
- 不定 patchmud ranked 榜 → 封套欄位的映射、不定實測／預設混合 provenance 的投影（`#454`）。
- 不定 `invariant_ceiling` 的實測估計方法（`#210` estimator 既有範圍）。
- 不修訂 `#209` R2 契約（`#452` §B 已論證不需要；本票 R2／R4 沿用其缺省語意）。
- 不擴充 registry roster、不決定哪些 (executor, persona) 組合該評測（`#456`）。

## 驗收面

- 四欄位各有唯一定案值（R1–R3），且每個值的推導可逐條回溯到本文件引用的程式碼行號或已查證
  的資料事實；拿掉任一推導錨點，對應定案即失去依據——用以確認不是拍腦袋。
- 存放機制唯一定案（R4：`DEFAULT_ENVELOPE` per-persona 常數、查表投影套用），並含對
  「寫進每列」的明確否決理由。
- R6 三個測試的規格足以讓 `#452` 實作票直接照做：`#452` 落地 PR 的測試若缺 T1/T2/T3 任一，
  即不滿足 `#453` 驗收「有回歸測試證明（不是人工比對）」。
- 本文件引用的行號皆以 main @ `ea76673`（v0.1.6）核對；`#452` 實作時若行號漂移，以引用的
  符號名（函式／常數）為準。
