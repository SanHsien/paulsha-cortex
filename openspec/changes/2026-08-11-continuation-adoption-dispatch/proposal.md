---
status: accepted
work_item: continuation-adoption-dispatch
---

## Goals

定案 issue #395「cortex 無法接手 mid-flight worktree」的架構決策——`feature-oneshot`
一系（含 #324 的 `small-fix`）目前僅有「從 origin target branch 開全新 worktree、
依凍結 plan 從頭實作」單一 slice 型態，完全無法承接四類續作型工作（進行到一半的
merge、lane worktree 大量 uncommitted WIP、已完成未併入的 lane 分支序列、既有
分支的驗證與 fixup）。本票定案 continuation slice 的 schema、dispatch 如何
bypass fresh-worktree 建立而 adopt 既有路徑、mid-merge 偵測與「完成 merge
視為 build step、禁止 abort」語意，以及最核心的設計張力——adopt 一個
（可能 dirty 的）既有 worktree 與 cortex 既有的 exact-candidate 純度／
pinned-input 契約如何調和。**本票以設計文件為主要交付，僅落地一個可安全
獨立分離、唯讀、不接線任何既有機制的 MVP（mid-merge 偵測 helper），不對
`paulsha_cortex/coordinator/{autonomy,dispatcher,manager,verification}.py`
等 dispatch/gate 核心檔案做任何改動**——這些檔案的實際改動規模與風險，
經本次設計查證，需要拆成後續多張獨立 code 票（見 `tasks.md`），不適合單票
一次到位。

## Why

issue #395 原文列出四類現場實際卡住的續作工作，並指出 `feature-oneshot` deck
沒有任何 deck/action 能：adopt 一個既有（可能 dirty）的本地 worktree 路徑、
從 mid-merge 狀態（`MERGE_HEAD` + staged resolution）續走、以「完成既有 diff
的收尾」為完成定義。本次查證（main @ `6626949`）逐一核對 issue 的三點建議，
發現與官方建議有出入、需要 maintainer 拍板的地方：

1. **issue 建議「完成定義改為可宣告式 gate（測試命令＋乾淨 working tree＋
   commit 存在）」——查證發現這件事已經存在**，不需要新 schema。
   `verification` frontmatter 契約（`validate_verification_contract`，
   `paulsha_cortex/coordinator/verification.py:207-303`）本來就是
   `tests`／`full_suite`（測試命令）＋`run_result_verification`
   （`verification.py:638-740`）的 `candidate-worktree-dirty`（乾淨 working
   tree，`:712-726`）／`candidate-not-advanced`（commit 存在，`:727-728`）
   ／ancestry（`:730-740`）三項 fail-closed 檢查——這正是 issue 想要的
   「宣告式 gate」，只是至今只被「從 plan 從頭實作」的 slice 使用過。真正
   缺的不是 gate schema，是「除了 plan-driven builder 之外，還有一種能把
   既有 worktree／branch 接進同一套 gate 的 slice 型態」（見 `design.md`
   D1／D7，類比 `openspec/changes/2026-08-07-design-adhoc-oneshot-dispatch`
   對 #338 的同類型「查證更正 issue 假設」）。
2. **issue 建議「spec 可指定 `existing_worktree`／`existing_branch`」——
   查證發現這需要繞過的不只是 `Dispatcher.dispatch()` 的
   `worktree_creator.create()` 呼叫，還有 `autonomy.dispatch_ready()`
   內建、深植於分支命名慣例（`_branch_for_slice(slice_id)` →
   `feature/<slice_id>`，`autonomy.py` 第 515／558／657／692 行四處呼叫）
   的假設，以及 `ScriptWorktreeCreator.create()`
   （`seams.py:100-119`）既有「同名分支存在時強制 reset 到 base」的
   landmine——continuation 若照抄既有「同名 branch 復用」路徑，會直接摧毀
   續作要保留的既有 commit 歷史。這比官方 issue 描述的「跳過 fanout 的
   fresh worktree 建立」更深入既有程式碼的假設層，是本票查證到、issue
   原文未涵蓋的新事實（見 `design.md` D2）。
3. **issue 建議「mid-merge 狀態偵測：把完成 merge 當 build step，禁止
   abort」——查證發現既有 ancestry 不變量已經結構性地懲罰 abort**，不需要
   新的強制機制：`run_result_verification` 要求 `dispatch_base`（target
   分支 tip）必須是 `candidate` 的 ancestor（`verification.py:730-740`），
   若 builder 把進行中的 merge `abort` 掉，產出的 candidate 不會納入
   target 的最新變更，這條既有檢查會直接把它判 `candidate-not-descendant`
   → `needs_human`，完全不需要新程式碼。mid-merge 偵測本身（本票已落地的
   `paulsha_cortex/coordinator/mid_merge.py` MVP）因此定位為
   **observability／prompt 塑形用途**，不是新增一道強制關卡（見 `design.md`
   D4）。

最關鍵、本票**明確不替 maintainer 決定**的張力：continuation 要 adopt 的
既有 diff，並非在 cortex 自己的 persona-contract／scope 檢查／`tdd-red`
紀律下產生——它可能是操作者手動寫的、或另一個 agent 在 cortex 監督範圍外
產生的。cortex 現有的「exact Candidate」信任鏈（`openspec/specs/
trusted-dispatch-completion/spec.md` 的「Candidate必須接受deterministic
ResultVerification」）隱含假設「`dispatch_base..candidate` 整段 diff皆由
單一、persona-bound、scope-checked 的 builder session 產生」。continuation
場景下這個假設不成立，但本票論證：純度不變量本身（乾淨 tree／SHA 前進／
target-ancestor）**不需要修改**——它管的是**退出邊界**（job 結束時的狀態），
不是**進入邊界**（builder session 開始時繼承的狀態）；adopt dirty 只動
進入邊界。真正未決的是**審查範疇**：ForeignReview／`verification.checks`
應該評估「adopt 之後、cortex 自己驅動的那一小段增量 diff」，還是「整個
`dispatch_base..candidate`（含 adopt 之前、cortex 從未監督過的既有內容）」
——這牽動要不要新增第二個 baseline SHA、要不要對 continuation candidate
要求比一般 slice 更高的審查強度。本票在 `design.md` D5 完整攤開兩個選項與
各自代價，**不擅自替 maintainer 決定**。

## What Changes（設計層級為主，僅含一個唯讀 MVP）

- 定案 D1：continuation slice 的 frontmatter schema——新增單一巢狀欄位
  `continuation`（非三個平行欄位），與 `EMITTED_FRONTMATTER_FIELDS`
  （`paulsha_cortex/deck/schema.py:12-22`）／`_normalize_frontmatter` 的
  `allowed` 集合（`autonomy.py:122-132`）的既有雙向等式如何擴充（機制上
  由既有 `tests/test_deck_contract_alignment.py` 的 set-equality 斷言
  機械驗收，不需新測試）。`plan`／`verification`／`target_branch` 等既有
  必要契約**不因 continuation 而免除**。
- 定案 D2：dispatch 端新增一個與 `Dispatcher.dispatch()`
  （`dispatcher.py:109-139`）平行、獨立的 adoption 進場點，不修改
  `dispatch()` 本身；點名 `autonomy.dispatch_ready()` 內建的
  `feature/<slice_id>` 分支命名假設與 `ScriptWorktreeCreator.create()`
  的既有分支強制 reset landmine，兩者皆是 continuation **不能重用**、必須
  繞開的既有路徑。
- 定案 D3：adoption 前的安全驗證——`existing_worktree`／`existing_branch`
  是否確實屬於目標 repo、是否已被其他 in-flight job 佔用、`adopt_dirty`
  未顯式宣告時對 dirty worktree fail-closed 拒收（沿用
  `model_identities.py` shadow-conflict fail-closed 的既有設計語彙）。
- 定案 D4：mid-merge 偵測——落地唯讀 helper
  `paulsha_cortex/coordinator/mid_merge.py::detect_merge_state()`
  （本票**唯一** code 交付，見下）；論證既有 ancestry 不變量已結構性阻擋
  「abort 後假裝完成」，偵測結果的用途限定在 observability／prompt 塑形。
- 定案 D5：**未替 maintainer 決定**——adopt dirty worktree 產生的 candidate，
  審查範疇應為「adopt 後增量 diff」或「`dispatch_base..candidate` 全段」，
  兩個選項與其代價並列於 `design.md`，留待 maintainer 拍板。
- 定案 D6：治理骨架不放寬——continuation 沿用既有 7-phase combo 骨架
  （比照 `openspec/changes/2026-08-07-design-adhoc-oneshot-dispatch` D3
  重用 `small-fix` 的既有立場），不新增更輕量 combo、不跳過 planning／
  review phase。
- 定案 D7：完成定義——**查證更正**：issue 建議的「可宣告式 gate」已由既有
  `verification` 契約提供，不新增 gate schema；唯一保留待決的子問題是
  「零新 commit 的『純驗證＋簽核』情境」是否需要新的 opt-out，或一律要求
  至少一個（可為 no-op marker）commit——見 D5 附近討論，同樣留待
  maintainer 決定。
- 定案 D8：GC／生命週期邊界——**確認、非變更**：`cortex work gc` 的
  `scan()` 已經以 `worktree_root` 邊界排除任何不在其 pool 內的 worktree
  （`gc.py:302` 的 `_is_under(resolved, pool_root)`），且即使 adopted
  worktree 恰好落在 pool 內，既有 dirty-worktree 保護
  （`gc.py:244-245`）在整個 continuation 進行期間也天然防止誤回收；本票
  不改 `gc.py` 任何一行。
- **唯一落地的 code**：`paulsha_cortex/coordinator/mid_merge.py`
  （`detect_merge_state()`，純唯讀、零接線）與
  `tests/test_mid_merge.py`（6 個回歸測試，含真實 `git worktree add` +
  真實衝突 merge fixture）。不觸碰 `autonomy.py`／`dispatcher.py`／
  `manager.py`／`verification.py`／`seams.py`／`deck/schema.py` 任一行。

## Capabilities

### Modified Capabilities

- `trusted-dispatch-completion`：新增「continuation/adoption 型 dispatch」
  的 contract delta，詳見 `specs/trusted-dispatch-completion/spec.md` 的
  ADDED Requirements，與 `docs/superpowers/specs/
  continuation-adoption-dispatch-spec.md` 的完整 Requirements、`docs/
  superpowers/specs/continuation-adoption-dispatch-design.md` 的 Decisions
  與未決問題清單。
