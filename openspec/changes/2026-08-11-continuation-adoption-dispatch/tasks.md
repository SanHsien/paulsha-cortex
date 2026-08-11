---
status: accepted
work_item: continuation-adoption-dispatch
---

# Tasks

design-doc 票（規模較大的新 slice 型 feature gap，比照 #210／#275／#279
既有慣例以設計文件交付），非 code TDD RED/GREEN 主體；例外是本票額外落地
一個可安全獨立分離的唯讀 MVP（`mid_merge.py`），該部分**有**走 TDD
（fixture-first：先以真實 git worktree + 衝突 merge 場景驗證行為，非空泛
斷言）。

- [x] 1.1 `proposal.md`／`design.md`／
      `specs/trusted-dispatch-completion/spec.md` 三件套完整，且與
      `docs/superpowers/specs/continuation-adoption-dispatch-{spec,design}.md`
      內容一致（openspec 三件套為摘要、docs/superpowers 為完整論證，兩者
      不得互相矛盾）。
- [x] 1.2 `docs/superpowers/specs/continuation-adoption-dispatch-spec.md`
      的 R1–R7 逐條對應 issue #395 原文四類情境之一或建議段落之一，且每條
      皆指出對應 D 決策與至少一個 main 上現有檔案／函式作為改動錨點（非
      空泛陳述）。
- [x] 1.3 D5／D7 的未決問題（審查範疇 all-diff vs incremental-diff、
      零新 commit 情境是否開 opt-out）明確標示為「本票不替 maintainer
      決定」，不得在 frontmatter 或內文以 TBD 呈現、亦不得自行拍板——這是
      本票刻意保留給 maintainer 的架構決策，見 `design.md` D5／D7 與 spec
      文件對應 Requirement 的「未決」小節。
- [x] 1.4 `paulsha_cortex/coordinator/mid_merge.py`
      （`detect_merge_state()`）與 `tests/test_mid_merge.py`（6 個回歸
      測試：無 merge／真實衝突 merge／完成 merge 後恢復乾淨／worktree 內
      MERGE_HEAD 為 worktree 私有狀態（非共用 `.git`）／git_runner 失敗
      fail-open／注入 fake git_runner 驗證呼叫序）。任一測試皆不得涉及真實
      `~/.agents`／`paulsha-cortex-worktrees` 路徑。
- [ ] 1.5 本設計文件經至少一輪 review（人工或 reviewer persona）——**本票
      由單一 agent 一次性產出全部交付，尚未經任何外部 review pass**，
      刻意保留未勾，不自我勾完就 claim done；D5／D7 的未決問題尤其需要
      maintainer 或 reviewer 過目後才適合視為真正 `accepted`。
- [x] 1.6 `changelog.d/continuation-adoption-design.md` fragment 與
      `CHANGELOG.md [Unreleased]` entry（#395）。
- [x] 1.7 `python3 -m pytest -q tests` 全套跑過（含新增 6 個 `mid_merge`
      測試）；`openspec validate --changes --strict` 對本 change 通過（或
      與既有 baseline 失敗項一致，需附複驗證據，比照
      `2026-08-07-design-model-capability-envelope` 的既有慣例，不得印象式
      宣稱）；帶 PR 上下文的 `policy_check` 0 fail（本票不開 PR，故此項由
      後續實際開 PR 時執行，此處只記錄要求不做裸跑宣稱）；`git diff
      --check` 乾淨。

## 本票不做（範圍切分給後續實作票）

- 不修改 `paulsha_cortex/coordinator/autonomy.py`（`dispatch_ready()`／
  `pin_dispatch_inputs()`／`_resolve_target_base_sha()`／
  `_launcher_worktree()` 任一函式）。
- 不修改 `paulsha_cortex/coordinator/dispatcher.py`（不新增
  `Dispatcher.adopt()` 本體）。
- 不修改 `paulsha_cortex/coordinator/seams.py`（`ScriptWorktreeCreator`
  的既有分支強制 reset 行為維持不變，只在設計文件記錄「continuation 不能
  重用這條路徑」）。
- 不修改 `paulsha_cortex/coordinator/verification.py`（純度不變量、
  `validate_verification_contract` 皆不動）。
- 不修改 `paulsha_cortex/coordinator/manager.py`（`dispatch_gate_scan()`
  等既有函式不動；D3 提到的「與 registry in-flight job 對帳」只是設計上
  建議重用其既有 `IN_FLIGHT_STATUSES` 過濾樣板，不代表本票已接線）。
- 不修改 `paulsha_cortex/deck/schema.py`／`paulsha_cortex/deck/data/
  cards.yaml`／`combos/*.yaml`（D1 的 `continuation` frontmatter 欄位、
  D6 的 continuation-aware build prompt 皆未落地程式碼）。
- 不解決 D5／D7 的未決問題本身（審查範疇、零 commit opt-out）——留給
  maintainer 拍板後的後續票。

## 後續應拆分的 code 票（建議，非本票範圍）

比照 `2026-08-07-design-adhoc-oneshot-dispatch` 拆碼慣例，避免單票過大：

1. **continuation frontmatter schema 落地**（D1）：
   - `deck/schema.py` 的 `EMITTED_FRONTMATTER_FIELDS` 新增 `continuation`；
     `autonomy.py` 的 `_normalize_frontmatter`／`parse_spec_frontmatter`
     同步新增解析與驗證（`mode`／`existing_worktree`／`existing_branch`／
     `adopt_dirty` 子欄位型別與互斥條件）。
   - 驗收：`test_deck_contract_alignment.py` 既有雙向等式測試自然涵蓋欄位
     完整性；新增 schema 驗證測試（互斥條件、路徑格式、`adopt_dirty` 預設
     值）。
2. **adoption dispatch 進場點**（D2＋D3，依賴票 1 的 schema）：
   - `Dispatcher.adopt()`（跳過 `worktree_creator.create()`）＋
     `autonomy.py` 內平行於 `dispatch_ready()` 的 adoption 呼叫路徑（不
     重用 `_branch_for_slice()` 的分支命名假設）。
   - D3 安全驗證（repo 歸屬、in-flight 佔用對帳、`adopt_dirty` fail-closed）
     一併落地。
   - 驗收：對一個真實建構的 dirty worktree／mid-merge worktree／既有
     branch 三種 fixture 各跑一次 adoption，既有 `dispatch()` 呼叫端行為
     位元不變（回歸測試）；`ScriptWorktreeCreator` 既有分支強制 reset
     行為不受影響（既有測試不變）。
3. **mid-merge 偵測接線**（D4，依賴票 2；本票已落地 `detect_merge_state()`
   本體，此票只做接線）：
   - continuation-aware `build_dispatch_prompt()` 變體（比照 #276 D3
     `task_slice` 參數先例）在偵測到 `MERGE_HEAD` 存在時，把衝突路徑與
     「完成 merge、禁止 abort」指示嵌入 build phase prompt。
   - 驗收：對已落地的 `mid_merge.detect_merge_state()` fixture 場景，
     prompt 內容含衝突檔案清單；既有（無 continuation）slice 的 prompt
     內容不變。
4. **maintainer 拍板 D5／D7 後的落地票**（依賴 maintainer 決策，故此為
   backlog 佔位，不預先假設答案）：
   - 若採 D5 選項 (b)（只評增量）：新增第二 baseline（`adoption_head`
     或等價欄位）貫穿 `run_result_verification`／`code-review`／
     `completion.py` 的 diff 範圍計算。
   - 若採 D7 的 opt-out：`validate_verification_contract` 新增顯式旗標
     （例如 `allow_zero_new_commits`），`run_result_verification` 的
     `candidate-not-advanced` 檢查改為條件式。
   - 驗收留待對應決策落地時的實作票定義（本票不預先寫死驗收條件，避免
     綁死 maintainer 尚未做的決定）。

## 驗收（本票）

三件套（openspec proposal/design/spec）與 docs/superpowers 完整文件皆存在
且互相一致；D1–D8／R1–R7 皆可證偽（每條指出改動錨點與「不做的後果」）；
D5／D7 明確記錄未決問題且不擅自拍板；`git diff` 只涉及
`openspec/**`／`docs/**`／`changelog.d/**`／`CHANGELOG.md`／
`paulsha_cortex/coordinator/mid_merge.py`／`tests/test_mid_merge.py`，
不觸碰 `autonomy.py`／`dispatcher.py`／`manager.py`／`verification.py`／
`seams.py`／`deck/schema.py`／`deck/data/**` 任一行。
