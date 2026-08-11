---
status: accepted
work_item: continuation-adoption-dispatch
---

# continuation-adoption-dispatch Specification

issue #395：`feature-oneshot`（含 #324 的 `small-fix`）一系 deck 一律從
origin target branch 開全新 worktree、依凍結 plan 從頭實作，無法接手四類
續作型工作：(1) 進行到一半的 merge（worktree 內 UU conflict＋staged
resolution）、(2) lane worktree 大量 uncommitted WIP、(3) 已完成未併入的
lane 分支序列、(4) 既有分支上的驗證與 fixup。本 spec 定案「continuation
slice」型態的契約，作為後續拆分 code 票的 Requirements 依據。**本票不實作
`autonomy.py`／`dispatcher.py`／`manager.py`／`verification.py`／
`seams.py`／`deck/schema.py` 任何一行，僅落地一個唯讀 MVP
（`mid_merge.py`）；R1–R7 全數為留待後續票落地的契約定案，非本票已完成的
行為。**

## 背景

本次查證（main @ `6626949`）核對 issue 原文三點建議與現有程式碼行為：

- `paulsha_cortex/coordinator/dispatcher.py:109-139` 的 `Dispatcher.dispatch()`
  一律呼叫 `self._worktree_creator.create(branch, base_sha=...)`
  （第 122 行）；`paulsha_cortex/coordinator/seams.py:70-135` 的
  `ScriptWorktreeCreator.create()` 對已存在目錄 fail-closed 拒絕（第 76-77
  行），對已存在**同名 branch**則走完全不同分支：驗證該 branch 是 base 的
  ancestor 後，`git branch -f branch exact_base`（第 116 行）**強制 reset**
  該 branch 到 base——這條路徑設計給「retry-build 等復原動作重派同一
  slice_id」場景，continuation 若誤用會直接摧毀要保留的既有 commit。
- `paulsha_cortex/coordinator/autonomy.py` 的 `dispatch_ready()`
  （448-598 行）內建分支命名假設：`_branch_for_slice(slice_id)` 求值出
  `feature/<slice_id>`，於第 515、558、657、692 行四處呼叫，貫穿
  baseline 取值（`early_dispatch_head`／`dispatch_head`）與 worktree 建立
  （`_launcher_worktree`，第 653-663 行）。continuation 要 adopt 的既有
  branch 名稱由操作者決定，不遵循此慣例。
- `paulsha_cortex/coordinator/verification.py:638-740` 的
  `run_result_verification()` 三項退出邊界檢查：`candidate-worktree-dirty`
  （712-726 行，worktree 必須乾淨）、`candidate-not-advanced`（727-728 行，
  candidate 必須異於 dispatch base）、ancestry（730-740 行，dispatch base
  必須是 candidate 的 ancestor）。這三項檢查合起來就是 issue 建議的「可
  宣告式 gate（測試命令＋乾淨 working tree＋commit 存在）」——`tests`／
  `full_suite` 測試命令欄位已存在於 `validate_verification_contract()`
  （207-303 行）。
- 全 repo `grep -rn "MERGE_HEAD"` 零命中——mid-merge 偵測是全新領域，本票
  新增 `paulsha_cortex/coordinator/mid_merge.py` 填補。
- `paulsha_cortex/coordinator/gc.py:281-303` 的 `scan()` 已用
  `worktree_root` pool 邊界（第 302 行 `_is_under(resolved, pool_root)`）
  排除任何不在其管理範圍內的 worktree；`_classify_worktree()`
  （226-258 行）對 dirty worktree 一律 `KEEP`（244-245 行）。

## Goals

- 定案 continuation slice 的最小 schema 擴充（一個巢狀欄位，不擴散既有
  `EMITTED_FRONTMATTER_FIELDS` 雙向等式的維護面）。
- 定案 dispatch 端如何在不修改 `Dispatcher.dispatch()`／不誤用既有分支
  強制 reset 路徑的前提下，adopt 既有 worktree／branch。
- 明確劃出「查證後發現已被既有機制滿足」的範圍（完成定義的宣告式 gate、
  abort 的結構性懲罰），避免重複造輪。
- 明確列出未替 maintainer 決定的架構取捨（審查範疇、零 commit 情境），
  不在本票內自行拍板。
- 未使用 continuation 的既有 slice（`fanout`／`tick`／`work` 既有入口）
  行為位元不變。

## Requirements

### R1 Continuation slice MUST以單一巢狀frontmatter欄位宣告，MUST NOT豁免既有pinned-input前提（對應 D1）

`continuation` 欄位 SHALL 為物件，子欄位 `mode`（`adopt-worktree` 或
`adopt-branch`）、`existing_worktree`（`mode=adopt-worktree` 時必要，絕對
路徑）、`existing_branch`（`mode=adopt-branch` 時必要）、`adopt_dirty`
（布林，預設 `false`）。`EMITTED_FRONTMATTER_FIELDS`
（`paulsha_cortex/deck/schema.py:12-22`）SHALL 新增此單一 key；
`_normalize_frontmatter` 的 `allowed` 集合（`autonomy.py:122-132`）與
`parse_spec_frontmatter` 回傳 `meta` 的預設值（`autonomy.py:75-86`）SHALL
同步新增，三處變動由既有雙向等式測試
（`tests/test_deck_contract_alignment.py::test_frontmatter_fields_match_runtime_contract`）
機械驗收。`plan`／`target_branch`／`verification` 三個既有 `dispatch: auto`
必要欄位（`autonomy.py:152-183`）SHALL 對 continuation slice 維持必要，
MUST NOT 因宣告 `continuation` 而被豁免。

若不做：若允許 continuation slice 略過 `plan`／`verification`，會讓
continuation 繞過既有 pinned-input 契約（`pin_dispatch_inputs()`，
`autonomy.py:245-266`）與 completion 端的 hash 比對
（`completion.py:600-604`），使 continuation 成為契約系統外的特例入口，
違反本 spec Goals 的「不擴散維護面」原則。

#### Scenario: continuation slice仍需宣告plan與verification

- **WHEN** slice spec宣告`dispatch: auto`與`continuation.mode:
  adopt-worktree`但未宣告`plan`
- **THEN** frontmatter解析MUST同既有行為一樣raise
  `ContractValidationError`（"auto dispatch requires a plan path"）

#### Scenario: 新增欄位機械驗收

- **WHEN** `EMITTED_FRONTMATTER_FIELDS`新增`continuation`
- **THEN** `test_frontmatter_fields_match_runtime_contract`仍為綠燈，
  不需另外新增等式測試

### R2 Adoption dispatch MUST為獨立進場點，MUST NOT重用既有分支強制reset路徑或`_branch_for_slice`命名假設（對應 D2）

系統 SHALL 新增與 `Dispatcher.dispatch()`（`dispatcher.py:109-139`）平行
的 adoption 進場點。`mode=adopt-worktree` 時 SHALL 直接使用
`existing_worktree` 路徑作為 job 的 worktree，MUST NOT 呼叫
`worktree_creator.create()`。`mode=adopt-branch` 時若需要新建 worktree
checkout 該 branch，MUST NOT 呼叫 `ScriptWorktreeCreator.create()` 既有的
「同名 branch 存在 → `git branch -f branch exact_base` 強制 reset」路徑
（`seams.py:100-119`）——該路徑會摧毀 continuation 要保留的既有 commit
歷史。`autonomy.dispatch_ready()` 內建的 `_branch_for_slice(slice_id)`
分支命名假設（`autonomy.py:515,558,657,692`）MUST NOT 被 continuation
adoption 路徑直接重用；SHALL 改為使用 spec 宣告的實際 branch 名稱貫穿
baseline 取值與 job 記錄。

若不做：若 continuation 誤用既有分支復用路徑，操作者精心保留的既有
commit 歷史會被 `git branch -f` 靜默清空，這是本設計查證到的、比 issue
原文「跳過 fresh worktree 建立」更深一層、後果更嚴重的既有程式碼陷阱。

#### Scenario: adopt-worktree不建立新worktree

- **WHEN** continuation slice以`mode: adopt-worktree`派工
- **THEN** dispatch MUST NOT呼叫`worktree_creator.create()`
- **THEN** job的`worktree`欄位等於`existing_worktree`宣告值

#### Scenario: adopt-branch不摧毀既有commit

- **WHEN** continuation slice以`mode: adopt-branch`宣告一個領先於任何
  `dispatch base`的既有branch（該branch有dispatch base之外的commit）
- **THEN** adoption完成後該branch的既有commit MUST仍存在於其歷史中
  （不得被`git branch -f`重置到base）

### R3 Adoption MUST先驗證repo歸屬與in-flight佔用，dirty worktree MUST NOT在未顯式opt-in下adopt（對應 D3）

Adoption 前，系統 SHALL 驗證 `existing_worktree` 是一個有效 git working
tree（`git rev-parse --is-inside-work-tree`）且其 git common dir 與目標
repo 一致（防止路徑指向無關 repo）。系統 SHALL 對照 registry 現有
`list_jobs()`（沿用 `manager.dispatch_gate_scan()` 已有的
`IN_FLIGHT_STATUSES` 過濾樣板，`manager.py:2131-2133`）確認沒有其他
in-flight job 已佔用同一 worktree 路徑或 branch 名稱。`existing_worktree`
非乾淨（`git status --porcelain --untracked-files=all` 非空）且
`continuation.adopt_dirty` 非顯式 `true` 時，adoption MUST fail-closed
拒絕，不得靜默略過。

若不做：若 dirty worktree 可在未顯式宣告下被 adopt，等同讓任何路過的
spec 意外接管操作者尚未準備好交出的本地狀態；若不做 in-flight 佔用檢查，
兩個 slice 可能同時操作同一物理目錄，造成不可預期的競態寫入。

#### Scenario: 未顯式adopt_dirty時拒絕dirty worktree

- **WHEN** `existing_worktree`路徑有未commit變更且spec未宣告
  `adopt_dirty: true`
- **THEN** adoption fail-closed拒絕，不建立job

#### Scenario: 路徑指向無關repo

- **WHEN** `existing_worktree`是一個有效git worktree，但其git common dir
  與目標repo不同
- **THEN** adoption fail-closed拒絕，錯誤訊息指出repo不符

### R4 Mid-merge偵測MUST為唯讀helper，MUST NOT驅動任何git寫入操作（對應 D4，本票已落地）

系統 SHALL 提供 `paulsha_cortex.coordinator.mid_merge.detect_merge_state()`
——讀 `git rev-parse --git-path MERGE_HEAD`（正確解析 worktree 私有路徑，
非共用 `.git`）與 `git status --porcelain=v2` 的 `u ...`（unmerged）行，
回傳是否有進行中的 merge、`MERGE_HEAD` 指向的 SHA、未解衝突路徑清單。
本函式 MUST NOT 執行任何 git 寫入操作（不 commit／不 abort／不
resolve）；讀取失敗（非 git repo、路徑不存在）MUST fail-open 回傳
「無進行中 merge」，不 raise。

若不做（若改為在此函式內驅動「自動完成 merge」等寫入操作）：唯讀
helper 與「驅動實際 git 操作」是完全不同風險等級的變更，混在一起會讓
observability 用途的程式碼帶有副作用風險，且尚未有後續票定案 build
card 該如何消費偵測結果之前，貿然寫入操作沒有上游契約可循。

#### Scenario: worktree內有真實衝突merge

- **WHEN** worktree存在`MERGE_HEAD`且`git status --porcelain=v2`回報`u`
  開頭的未解衝突行
- **THEN** `detect_merge_state()`回傳`in_progress=True`，`merge_head`
  等於`MERGE_HEAD`內容，`unmerged_paths`含衝突檔案路徑

#### Scenario: git worktree的MERGE_HEAD為私有狀態

- **WHEN** 兩個worktree（各自checkout不同branch）之一正處於merge衝突，
  另一個worktree（例如主repo）無任何進行中的merge
- **THEN** 對前者呼叫`detect_merge_state()`回傳`in_progress=True`，對後者
  回傳`in_progress=False`——兩者互不干擾

#### Scenario: 既有ancestry不變量已結構性懲罰abort

- **WHEN** builder在偵測到`MERGE_HEAD`後執行`git merge --abort`並以此
  狀態結束job
- **THEN** `run_result_verification`的ancestry檢查
  （`verification.py:730-740`）MUST判定dispatch base非candidate的
  ancestor，導向`needs_human`——此行為由既有機制提供，不依賴
  `detect_merge_state()`的偵測結果

### R5 Continuation candidate仍MUST滿足現行exact-candidate純度不變量（對應 D5，核心張力，本票不替maintainer決定審查範疇）

Continuation slice 的 candidate MUST 通過與非 continuation slice 完全相同
的退出邊界檢查（worktree 乾淨、candidate 較 dispatch base 前進、
dispatch base 為 candidate 的 ancestor，`verification.py:706-740`）。
「adopt dirty worktree」SHALL 只影響 builder session 開始時繼承的進入
邊界狀態，MUST NOT 被實作為放寬上述任何一項退出邊界檢查。

**未決（本 spec 不裁定）**：`dispatch_base..candidate` 全段 diff 混合了
「adopt 前、cortex 從未監督的既有內容」與「adopt 後、cortex 驅動的增量
內容」。ForeignReview／`verification.checks` 應評估全段還是只評估增量段，
需要新增第二 baseline（例如 `adoption_head`）才能技術上支援「只評估
增量」；本 spec 記錄兩個選項與代價（見對應 design 文件 D5），MUST 由
maintainer 明確拍板後才可落地，不得由實作票自行選邊。

若不做（若在本票內擅自選邊）：審查範疇直接決定 continuation candidate
的信任邊界寬窄，是本設計中風險係數最高的單一決策點，理應由 maintainer
在看過兩個選項的完整代價分析後親自決定，不適合由單一設計票或後續實作票
單方面拍板。

#### Scenario: continuation candidate結束時仍dirty

- **WHEN** continuation slice的builder job結束但worktree仍有未commit
  變更
- **THEN** verification MUST將該slice導向`needs_human`，判定路徑與非
  continuation slice完全相同

#### Scenario: 審查範疇取捨留待maintainer決定

- **WHEN** continuation candidate的`dispatch_base..candidate`同時含
  adopt前既有內容與adopt後增量內容
- **THEN** 本spec不裁定reviewer應評估全段或僅評估增量，此問題MUST留至
  maintainer拍板後的後續票

### R6 完成定義MUST重用既有verification契約，MUST NOT新增宣告式gate schema（對應 D7，查證更正issue假設）

Continuation slice 的完成定義 SHALL 直接沿用既有 `verification` frontmatter
契約（`validate_verification_contract()`，`verification.py:207-303`）的
`tests`／`full_suite`（測試命令）欄位，與 `run_result_verification()` 既有
的 `candidate-worktree-dirty`（乾淨 working tree）／`candidate-not-advanced`
（commit 存在）兩項檢查（`verification.py:712-728`）。系統 MUST NOT 為
continuation 新增另一套宣告式 gate schema——issue 建議的能力已由既有機制
提供。

**未決（本 spec 不裁定）**：型 4「純驗證＋簽核、可能零新 commit」情境下，
`candidate-not-advanced` 不變量（candidate 必須異於 dispatch base）是否
需要 opt-out，或一律要求至少一個（可為 `--allow-empty` no-op）commit
維持不變量不變——留待 maintainer 決定，本 spec 不預設答案。

若不做（若新增平行的宣告式 gate schema）：會與既有 `verification` 契約
形成兩套語意重疊但互相獨立的完成定義機制，增加維護面且違反本 repo
一貫的「重用既有機制、不重複造輪」設計原則（比照 #279 D3 對 combo
骨架的相同立場）。

#### Scenario: continuation沿用既有verification契約

- **WHEN** continuation slice宣告`verification.tests`與
  `verification.full_suite`
- **THEN** `run_result_verification()`對其套用與非continuation slice
  完全相同的檢查邏輯，不經任何continuation專屬分支

#### Scenario: 零新commit情境留待maintainer決定

- **WHEN** continuation slice的既有diff已完整涵蓋所有必要變更，build
  phase未產生任何新commit
- **THEN** 本spec不裁定`candidate-not-advanced`是否對此情境開放
  opt-out，此問題MUST留至maintainer拍板

### R7 Adopted worktree的生命週期MUST NOT併入既有GC回收範圍（對應 D8，確認非變更）

`cortex work gc`（`gc.py::scan()`，281-303 行）MUST 維持只掃描其配置的
`worktree_root` pool 邊界內的 worktree（既有行為，`gc.py:302` 的
`_is_under(resolved, pool_root)`）；adoption 使用的既有外部路徑 MUST NOT
被自動納入回收範圍。即使 adopted worktree 恰好落在 pool 內，既有
dirty-worktree 保護（`_classify_worktree()`，`gc.py:244-245`）MUST 繼續
在 continuation 進行期間防止誤回收——此為既有行為的確認，非本 spec 新增
的要求。

若不做（若刻意放寬 GC 掃描範圍納入外部路徑）：會讓 cortex 對操作者未曾
交給它管理的目錄取得刪除／reset 權限，明顯超出「adopt 既有狀態完成
它」的訴求範圍，且與 issue 原文完全無關——不應在本票或任何後續票主動
擴大 GC 的管轄邊界。

#### Scenario: adopted worktree路徑落在pool root之外

- **WHEN** `existing_worktree`路徑不在coordinator配置的worktree pool
  root之下
- **THEN** `cortex work gc`的掃描結果MUST NOT包含該路徑作為任何分類項目

#### Scenario: adopted worktree恰好落在pool root內但仍dirty

- **WHEN** `existing_worktree`路徑落在pool root內，且continuation尚未
  完成（worktree仍dirty）
- **THEN** `gc.scan()`對其分類MUST為`KEEP`／`REASON_DIRTY_WORKTREE`，
  與任何其他dirty worktree的既有判定邏輯相同
