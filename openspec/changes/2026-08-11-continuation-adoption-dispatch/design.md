---
status: accepted
work_item: continuation-adoption-dispatch
---

# continuation-adoption-dispatch Design

## Decisions

- **D1（schema）**：新增單一巢狀 frontmatter 欄位 `continuation`（非三個平行
  欄位），子欄位 `mode: adopt-worktree|adopt-branch`／`existing_worktree`
  （abs path）／`existing_branch`／`adopt_dirty`（預設 `false`，須顯式
  `true` 才允許 dirty adopt）。`EMITTED_FRONTMATTER_FIELDS`
  （`paulsha_cortex/deck/schema.py:12-22`）與 `_normalize_frontmatter` 的
  `allowed` 集合（`paulsha_cortex/coordinator/autonomy.py:122-132`）都要
  加這一個新 key；`parse_spec_frontmatter` 回傳的 `meta` dict 預設值同步加
  `"continuation": None`——三處同步是既有雙向等式（`tests/
  test_deck_contract_alignment.py::test_frontmatter_fields_match_runtime_contract`
  的 `assert set(EMITTED_FRONTMATTER_FIELDS) == set(meta) - {"path"}`）機械
  驗收的範圍，不需另寫新測試。`plan`／`target_branch`／`verification` 仍是
  `dispatch: auto` 的必要欄位（`autonomy.py:152-183`）——continuation 不豁免
  既有 pinned-input／governance 前提。
- **D2（dispatch bypass）**：新增與 `Dispatcher.dispatch()`
  （`dispatcher.py:109-139`）平行的 adoption 進場點（暫名
  `Dispatcher.adopt()`），跳過 `worktree_creator.create()`；`existing_branch`
  模式若需要新建 worktree，MUST NOT 走 `ScriptWorktreeCreator.create()`
  既有的「同名分支復用」路徑（`seams.py:100-119`，偵測到同名分支時執行
  `git branch -f branch exact_base` 強制 reset——會摧毀 continuation 要保留
  的既有 commit）。`autonomy.dispatch_ready()` 對分支名稱的假設
  （`_branch_for_slice(slice_id)` → `feature/<slice_id>`，見
  `autonomy.py:515,558,657,692` 四處呼叫）在 continuation 下不成立，需要
  平行於 `dispatch_ready()` 的獨立呼叫路徑，不能直接重用其內部分支推導。
- **D3（adoption 前安全驗證）**：`existing_worktree` MUST 先驗證
  `git -C <path> rev-parse --is-inside-work-tree` 為真，且其
  `git rev-parse --git-common-dir` 與目標 repo 的 common dir 一致（防止
  adopt 到無關 repo）；MUST 對照 registry `list_jobs()`（沿用
  `manager.dispatch_gate_scan()` 已有的 `IN_FLIGHT_STATUSES` 過濾樣板，
  `manager.py:2131-2133`）確認沒有其他 in-flight job 已佔用同一
  worktree／branch。`adopt_dirty` 非顯式 `true` 時，對非乾淨 worktree
  （`git status --porcelain --untracked-files=all` 非空）MUST fail-closed
  拒絕整次 adoption——語彙比照 `model_identities.py` 既有的 shadow-conflict
  fail-closed（多一個可疊加來源，衝突時拒絕，不靜默處理）。
- **D4（mid-merge 偵測，本票已落地）**：`paulsha_cortex/coordinator/
  mid_merge.py::detect_merge_state(worktree)` 讀 `git rev-parse --git-path
  MERGE_HEAD`（已以真實 `git worktree add` 核驗：worktree 的 `MERGE_HEAD`
  正確落在其私有 `.git/worktrees/<name>/MERGE_HEAD`，非共用 `.git`）與
  `git status --porcelain=v2` 的 `u ...` 行取得未解衝突路徑，純唯讀、不驅動
  任何 git 寫入。**論證**：既有 ancestry 不變量
  （`verification.py:730-740`，`merge-base --is-ancestor dispatch_base
  candidate`）已經結構性懲罰「abort 後假裝完成」——abort 後的 candidate
  不含 target 最新內容，`dispatch_base` 不再是其 ancestor，直接落
  `candidate-not-descendant` → `needs_human`。`detect_merge_state()` 的
  用途因此定位為 observability／build-phase prompt 塑形（「完成此 merge，
  不得 abort」的具體指示文字），不是新增一道獨立強制關卡；正式接線（哪個
  card 消費它、如何影響 dispatch prompt）留給後續實作票。
- **D5（核心張力，本票不替 maintainer 決定）**：純度不變量
  （`candidate-worktree-dirty`／`candidate-not-advanced`／ancestry，
  `verification.py:706-740`）管的是**退出邊界**，continuation 的
  dirty-adopt 只動**進入邊界**——這條不變量本身不需修改。但
  `dispatch_base..candidate` 全段 diff 在 continuation 下混合了「adopt 前、
  cortex 從未監督的既有內容」與「adopt 後、cortex 驅動的增量內容」，
  ForeignReview／`verification.checks` 該評估全段還是只評估增量段，是
  尚未解決、需要新增「第二個 baseline SHA」才能技術上支援「只評估增量」
  選項的架構決策。兩個選項與代價：(a) 評全段——沿用現有單一
  `dispatch_base` 模型，不需新欄位，但 reviewer 得對 cortex 完全沒監督過的
  程式碼負同等審查責任；(b) 評增量——需要新增 `adoption_head` 或等價的
  第二基準點，`run_result_verification` 與 `code-review` 的 diff 範圍都要
  跟著改，複雜度顯著增加，且「增量段獨立乾淨」不代表「全段組合起來正確」
  （例如 adopt 前的既有內容本身有問題，只審增量會漏檢）。本票不擅自選邊。
- **D6（治理骨架）**：比照 `openspec/changes/
  2026-08-07-design-adhoc-oneshot-dispatch` D3 的既有立場——continuation
  沿用 7-phase combo 骨架（`validate_manager_spine()` 涵蓋、persona 綁定、
  ship-前-reviewer），不新增更輕量 combo、不跳過 planning／review phase；
  build phase 的 dispatch prompt 改走 continuation-aware 的模板（比照
  `openspec/changes/2026-08-07-builder-task-boundary-segmentation` D3
  `build_dispatch_prompt()` 新增 optional 參數、未傳維持既有行為不變的
  既有先例），非另開新 card／combo。
- **D7（完成定義，查證更正 issue 假設）**：issue 建議「完成定義改可宣告式
  gate（測試命令＋乾淨 working tree＋commit 存在）」——查證發現這已是既有
  `verification` 契約（`validate_verification_contract`，
  `verification.py:207-303`）＋`run_result_verification` 三項檢查
  （`:706-728`）逐字提供的能力，continuation 不需要新 gate schema，直接
  沿用。唯一保留子問題（見 D5 附近）：型 4「純驗證＋簽核、可能零新
  commit」是否需要對 `candidate-not-advanced` 不變量開一個 opt-out，或
  一律要求至少一個（可為 `--allow-empty` no-op）commit——本票不決定。
- **D8（GC／生命週期邊界，確認非變更）**：`gc.scan()`
  （`gc.py:281-303`）已經以 `pool_root` 邊界（`_is_under(resolved,
  pool_root)`，第 302 行）排除任何不在 `worktree_root` 內的 worktree；
  即使 adopted worktree 恰好落在 pool 內，`_classify_worktree` 既有的
  dirty-worktree 保護（`gc.py:244-245`，`REASON_DIRTY_WORKTREE`）在整個
  continuation 進行期間也天然防止誤回收。本票不改 `gc.py` 任何一行，此為
  查證確認，非新增行為。

詳細 D1–D8 全文論證、風險緩解、四類 issue 情境對照與未決問題清單見
`docs/superpowers/specs/continuation-adoption-dispatch-design.md`
與 `docs/superpowers/specs/continuation-adoption-dispatch-spec.md`。
