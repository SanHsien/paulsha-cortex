---
status: accepted
work_item: continuation-adoption-dispatch
---

# continuation-adoption-dispatch Design

issue #395：2026-08-10 embedebuguide 收尾 issue #53–#67 時，四類「續作型」
現場工作全部無法交給 cortex——`feature-oneshot`（含 #324 的 `small-fix`）
deck 的 slice 一律從 origin target branch 開全新 worktree、依凍結 plan
從頭實作，沒有任何 deck/action 能 adopt 一個既有（可能 dirty）的本地
worktree 路徑、從 mid-merge 狀態續走、以「完成既有 diff 的收尾」為完成
定義。本文定案該能力（暫名 continuation slice）的架構決策，作為後續拆碼
票的單一依據。

## 背景與現況查證（main @ `6626949`）

issue 原文列出四類現場情境與三點建議。逐項重新查證：

| # | issue 情境 | 對應 continuation mode（本文定案） | 關鍵既有機制 |
|---|---|---|---|
| 1 | 進行到一半的 merge（worktree 內 3 個 UU conflict、其餘已 staged） | `adopt-worktree`（dirty，`MERGE_HEAD` 存在） | `mid_merge.detect_merge_state()`（D4，本票已落地）＋既有 ancestry 不變量（D4） |
| 2 | lane worktree 內大量 uncommitted WIP（15+ 檔案、含新測試） | `adopt-worktree`（dirty，無 `MERGE_HEAD`） | 既有 `candidate-worktree-dirty`／`candidate-not-advanced` 退出邊界檢查（D5／D7），不需新機制 |
| 3 | 已完成但未併入 integration 的 lane 分支序列合併（衝突集中在同一批核心檔） | 多個 `adopt-branch` slice 以既有 `depends_on` 鏈接（D2 附論） | 既有 `depends_on` 相依機制（`autonomy.py` `ready_units`），本文不新增序列合併原語 |
| 4 | 既有分支上的驗證與 fixup | `adopt-branch`（clean 或近乎 clean） | R6／D7 的「零新 commit」未決問題最直接對應此型 |

三點建議的查證結論（與 issue 原文期望有出入處）：

1. **「spec 可指定 `existing_worktree`／`existing_branch`，跳過 fanout 的
   fresh worktree 建立」**——查證發現需要繞開的不只是
   `Dispatcher.dispatch()`（`dispatcher.py:109-139`）本身，還有
   `autonomy.dispatch_ready()`（448-598 行）內建、深植於四處呼叫點的
   `feature/<slice_id>` 分支命名假設，以及 `ScriptWorktreeCreator.create()`
   （`seams.py:70-135`）既有的「同名 branch 強制 reset」landmine（見 D2）。
2. **「完成定義改可宣告式 gate（測試命令＋乾淨 working tree＋commit
   存在）」**——查證發現這件事已經被既有 `verification` 契約
   （`verification.py:207-303`＋`638-740`）逐字提供，continuation 不需要
   新 schema（見 D7）。
3. **「mid-merge 狀態偵測：有 MERGE_HEAD 時把完成 merge 當 build step，
   禁止 abort」**——查證發現既有 ancestry 不變量
   （`verification.py:730-740`）已經結構性懲罰 abort，偵測本身的角色是
   observability／prompt 塑形，不是新增強制機制（見 D4）。

## Decisions

### D1 Schema：單一巢狀 `continuation` frontmatter 欄位，不擴散既有雙向等式的維護面

**現況**：`paulsha_cortex/deck/schema.py:12-22` 的 `EMITTED_FRONTMATTER_FIELDS`
是「runtime 契約真相源」（模組內註解原文：「勿發明多餘欄位」），與
`paulsha_cortex/coordinator/autonomy.py:121-207` 的 `_normalize_frontmatter`
（其 `allowed` 集合，122-132 行）、`parse_spec_frontmatter`（63-118 行）的
預設 `meta` dict 三處必須維持精確的雙向等式，由
`tests/test_deck_contract_alignment.py::test_frontmatter_fields_match_runtime_contract`
機械斷言：

```python
assert set(EMITTED_FRONTMATTER_FIELDS) == set(meta) - {"path"}
```

**決策**：新增**單一**巢狀欄位 `continuation`（物件），而非三個平行欄位
（`existing_worktree`／`existing_branch`／`adopt_dirty` 各自獨立）——理由
是把 continuation 相關欄位的驗證邏輯（互斥條件：`mode=adopt-worktree`
必要 `existing_worktree`、`mode=adopt-branch` 必要 `existing_branch`，兩者
不得同時宣告）收斂在物件內部的專屬驗證函式，不讓 `_normalize_frontmatter`
本體因為三個新的頂層條件分支而膨脹。子欄位：

```yaml
continuation:
  mode: adopt-worktree      # 或 adopt-branch
  existing_worktree: /abs/path/to/dirty-worktree   # mode=adopt-worktree 時必要
  existing_branch: lane/foo-bar                     # mode=adopt-branch 時必要
  adopt_dirty: true          # 預設 false；existing_worktree 非乾淨時必須顯式 true
```

`plan`／`target_branch`／`verification` 三個既有 `dispatch: auto` 必要
欄位（`autonomy.py:152-183`）**不因宣告 `continuation` 而豁免**——
continuation 仍走與其他 slice 相同的 `pin_dispatch_inputs()`
（`autonomy.py:245-266`）契約 pin 流程，只是 worktree／branch 的**取得
方式**不同，不代表 continuation 是脫離既有治理骨架的特例入口（見 D6）。

### D2 Dispatch bypass：新增平行進場點，明確點名兩個不能重用的既有路徑

**現況**：`Dispatcher.dispatch()`（`dispatcher.py:109-139`）：

```python
def dispatch(self, *, task, persona, pane_id, command, base_sha=None, git_runner=None):
    branch = _branch_for_task(task)
    try:
        worktree = self._worktree_creator.create(branch, base_sha=base_sha)
    except TypeError:
        worktree = self._worktree_creator.create(branch)
    self._pane_sender.send(pane_id, command)
    ...
```

`_branch_for_task(task)`（39-40 行）硬編 `f"feature/{task}"`。
`ScriptWorktreeCreator.create()`（`seams.py:70-135`）對「branch 已存在」
的既有處理（100-119 行）：

```python
if branch_probe.returncode == 0:
    ancestor = subprocess.run([..., "merge-base", "--is-ancestor", branch, exact_base], ...)
    if ancestor.returncode == 1:
        raise ValueError("existing worktree branch has commits outside requested base")
    ...
    subprocess.run(["git", "-C", str(self._repo), "branch", "-f", branch, exact_base], check=True, ...)
    argv = ["git", "-C", str(self._repo), "worktree", "add", str(target), branch]
```

這條路徑設計給「同一 slice_id 重新派工、舊 branch 只是名字撞了但沒有
要保留的內容」場景（例如 retry-build）——它先驗證既有 branch 是 base 的
ancestor（防止誤刪領先內容），再用 `git branch -f` **把 branch 強制指回
base**，等於清空該 branch 上所有領先於 base 的 commit。continuation 的
`adopt-branch` 模式若誤用此路徑，會直接摧毀操作者想保留的既有工作——這是
本次查證發現、issue 原文未點名的具體 landmine。

`autonomy.dispatch_ready()`（448-598 行）另有四處呼叫
`_branch_for_slice(slice_id)`（與 `_branch_for_task` 同構，皆求
`feature/<slice_id>`）：

```python
# autonomy.py:515（early baseline，dispatch 前）
early_dispatch_head = runner(["rev-parse", _branch_for_slice(slice_id)])
# autonomy.py:558（真正 launch 前的 baseline）
dispatch_head = runner(["rev-parse", _branch_for_slice(slice_id)])
# autonomy.py:657（_launcher_worktree 內部）
branch = _branch_for_slice(slice_id)
# autonomy.py:692（_record_launching_job 呼叫端）
branch=_branch_for_slice(slice_id)
```

continuation 的 branch 名稱由操作者宣告（`existing_branch`，或
`existing_worktree` 當下 checkout 的 branch），與 `slice_id` 無固定對應
關係，四處呼叫點都要改讀 spec 宣告值而非重新推導。

**決策**：新增與 `dispatch_ready()` 平行、獨立的 adoption 呼叫路徑（暫名
`autonomy.adopt_ready()` 或等價實作，確切函式命名留給實作票），與新增的
`Dispatcher.adopt()`（跳過 `worktree_creator.create()`）搭配：

- `mode=adopt-worktree`：直接以 `existing_worktree` 作為 job 的
  `worktree`，branch 名稱從該路徑 `git rev-parse --abbrev-ref HEAD` 讀出
  （detached HEAD 時 fail-closed 拒絕——continuation 需要一個具名 branch
  才能沿用既有 `poll_done`／completion 流程對 branch head 的比對邏輯）。
- `mode=adopt-branch`：需要新建一個 worktree checkout 該既有 branch **在
  其當前 tip**（不重置到任何 base），實作上是 `git worktree add
  <target> <existing_branch>`（不含 `-b`，不呼叫 `git branch -f`）——這是
  一條 `ScriptWorktreeCreator` 現在不存在的第三種路徑（現有邏輯只有
  「新 branch」與「同名復用＋強制 reset」兩種），需要新增，不能從既有
  兩個分支修修改改湊出來。
- **前置條件**（由 git 本身的不變量帶出，非本設計新增）：`existing_branch`
  MUST NOT 在呼叫當下已被其他 worktree（含操作者自己的主要 checkout）
  checkout——`git worktree add` 對此會直接失敗並回報清楚的 stderr（"already
  checked out at ..."）。這對型 3／型 4 是自然成立的（操作者描述的是
  「已完成但未併入」「既有但非當前工作中」的分支，通常不會同時是操作者
  當下工作目錄所在的 branch）；若操作者恰好仍在該 branch 上工作，
  adoption 應 fail-closed 並把 git 的原始錯誤訊息回傳給操作者，而非嘗試
  自動切換操作者的工作目錄（那已經超出 cortex 的職責邊界）。

### D3 Adoption 前安全驗證：repo 歸屬、in-flight 佔用、dirty opt-in

**決策**：三項檢查，皆在建立 job 之前執行、任一失敗即 fail-closed 拒絕
整次 adoption（不建立 job、不消耗派工嘗試）：

1. **repo 歸屬**：`git -C <existing_worktree> rev-parse
   --is-inside-work-tree` 須為 `true`，且 `git -C <existing_worktree>
   rev-parse --git-common-dir`（解析為絕對路徑後）須與目標 repo 的
   common dir 一致。防止操作者手誤把路徑指到完全無關的另一個 repo。
2. **in-flight 佔用對帳**：對照 registry `list_jobs()`，過濾
   `status in IN_FLIGHT_STATUSES`（沿用 `manager.dispatch_gate_scan()`
   已有的過濾樣板，`manager.py:2131-2133`：
   `active = {j.get("task") for j in registry.list_jobs() if j.get("status")
   in IN_FLIGHT_STATUSES}`），確認沒有其他 in-flight job 的 `worktree`
   或 `branch` 欄位與本次 adoption 目標相同。防止兩個 slice 同時操作同一
   物理目錄造成競態寫入。
3. **dirty opt-in**：`git status --porcelain --untracked-files=all`
   非空且 `continuation.adopt_dirty` 非顯式 `true` 時 fail-closed 拒絕。
   語彙比照 `model_identities.py::load_model_identities()` 既有的
   shadow-conflict fail-closed 設計（instance-local 疊加來源與 packaged
   同鍵不同值即 raise，不靜默覆蓋）——這裡的「靜默」風險是「任何路過的
   spec 意外接管操作者尚未準備好交出的本地狀態」，性質相同：多一個資料
   來源（既有 dirty 狀態）必須顯式確認才生效，不能預設信任。

### D4 Mid-merge 偵測（本票已落地）：唯讀 helper，觀測用途，非新增強制機制

**決策**：新增 `paulsha_cortex/coordinator/mid_merge.py::detect_merge_state()`
——已在本票落地，見模組原始碼與 `tests/test_mid_merge.py`。核心行為：

```python
def detect_merge_state(worktree, *, git_runner=None) -> MergeState:
    ...
    merge_head_path_text = runner(["rev-parse", "--git-path", "MERGE_HEAD"]).strip()
    ...
    if not merge_head_path.is_file():
        return MergeState(in_progress=False)
    merge_head_sha = merge_head_path.read_text(...).strip() or None
    status_text = runner(["status", "--porcelain=v2"])
    return MergeState(in_progress=True, merge_head=merge_head_sha,
                       unmerged_paths=_parse_unmerged_paths(status_text))
```

已以真實 `git worktree add` 手動核驗：`git -C <worktree> rev-parse
--git-path MERGE_HEAD` 對 worktree 正確解析到其私有的
`<main-repo>/.git/worktrees/<name>/MERGE_HEAD`，非任何共用 `.git` 目錄
（見 `tests/test_mid_merge.py::test_conflicting_merge_detected_inside_git_worktree`，
同時驗證另一個 worktree 完全不受影響）；對非 worktree 的一般 repo，
`--git-path` 回傳相對於 `-C` 目錄的相對路徑，兩種情況函式皆正確處理。
`git status --porcelain=v2` 的 unmerged 行格式（`u <XY> <sub> <m1> <m2>
<m3> <mW> <h1> <h2> <h3> <path>`，固定 11 欄）已以真實衝突 fixture 核驗
（非憑印象假設格式）。

**為什麼只是唯讀、不驅動任何寫入**：既有 ancestry 不變量
（`verification.py:730-740`）：

```python
ancestry = _run_git(["-C", ..., "merge-base", "--is-ancestor", dispatch_base, candidate], ...)
if ancestry["status"] == "non-zero" and ancestry["returncode"] == 1:
    return _finish("needs_human", "candidate-not-descendant")
```

若 builder 在偵測到 `MERGE_HEAD` 後執行 `git merge --abort`，最終
candidate 不會包含 target 分支（`dispatch_base`）的最新變更，這條既有
檢查會直接判 `candidate-not-descendant` → `needs_human`——**不需要任何
新程式碼**就已經結構性阻擋「abort 後假裝完成」。`detect_merge_state()`
因此定位為：(a) observability（`cortex inspect status` 未來可顯示某
slice 是否正卡在 mid-merge）、(b) build-phase dispatch prompt 塑形的
輸入（把偵測到的衝突檔案清單具體嵌入 prompt，指示「完成此 merge，不得
abort」——比照 #276 D3 `build_dispatch_prompt()` 新增 optional 參數、
未傳維持既有行為的先例）。兩者皆為後續實作票的接線範圍，本票只交付
偵測本體。

### D5 核心張力：exact-candidate 純度管退出邊界，adopt dirty 只動進入邊界——但審查範疇未決

**現況**：`run_result_verification()` 的三項退出邊界檢查
（`verification.py:706-740`）：

```python
if worktree_status["stdout"].strip():
    return _finish("needs_human", "candidate-worktree-dirty")       # 乾淨 working tree
if candidate == dispatch_base.lower():
    return _finish("needs_human", "candidate-not-advanced")          # commit 存在
...
if ancestry["returncode"] == 1:
    return _finish("needs_human", "candidate-not-descendant")        # target ancestor
```

`openspec/specs/trusted-dispatch-completion/spec.md` 的「Candidate必須
接受deterministic ResultVerification」Requirement 隱含一個至今從未被
挑戰過的假設：`dispatch_base..candidate` 這一整段 diff，是由**單一、
persona-bound、scope-checked 的 builder session** 產生的——`checks`
（`persona-scope`）、`code-review` 的 ForeignReview，都是針對「這整段 diff
是不是這次 dispatch 授權範圍內產生的」設計。

**論證退出邊界不需修改**：continuation 的 dirty-adopt 只影響 builder
session **開始時**繼承的狀態（進入邊界）——builder session 本身仍然
必須把 worktree 收斂到乾淨、SHA 較 dispatch base 前進、dispatch base 為
其 ancestor 的終態才能被判定完成，這條「退出時必須怎樣」的規則完全不用
為 continuation 開特例。

**未解決的部分（本文不裁定）**：`dispatch_base..candidate` 這段 diff 在
continuation 下，內容混合了：

- **adopt 前**：操作者手動寫的、或另一個 agent 在 cortex 監督範圍外產生
  的既有內容（例如 issue 型 2 描述的「15+ 檔案改到一半、含新測試」）——
  這段內容從未經過 cortex 自己的 persona-scope 檢查、tdd-red 紀律、或
  任何形式的即時審查。
- **adopt 後**：cortex 這次 dispatch 驅動 builder session 產生的增量
  內容（可能只是「解決 3 個 UU 衝突 + 一個 commit」這麼小）。

現行架構下 `checks`／ForeignReview 的 diff 範圍固定是
`dispatch_base..candidate`（全段），沒有第二個 baseline 可以切出「只看
adopt 後那一小段」。兩個選項：

- **選項 (a) 評全段（維持現行單一 baseline 模型）**：優點是不需要新增
  任何欄位或改動 `run_result_verification`／`code-review` 的 diff 範圍
  計算邏輯，continuation candidate 與一般 candidate 走完全相同的審查
  路徑。缺點：reviewer 得對 cortex 完全沒監督過的既有內容（可能是操作者
  自己都還沒 review 過的 WIP）負同等審查責任，若審查強度沿用現行標準
  （單一 reviewer、單輪 verdict），對「15+ 檔案的既有 WIP」這種規模的
  審查負擔可能名不符實地輕。
- **選項 (b) 評增量（新增第二 baseline）**：新增 `adoption_head`（或等價
  欄位，記錄 adoption 當下的 candidate SHA），`run_result_verification`
  與 `code-review` 的 diff 範圍改成 `adoption_head..candidate`。優點是
  審查聚焦在 cortex 真正驅動、有把握的那一小段。缺點：(1) 複雜度顯著
  增加——`run_result_verification` 現在單一 `dispatch_base` 貫穿 ancestry
  ／artifact／scope 多處檢查，拆成兩個 baseline 需要逐一重新論證每項
  檢查該用哪一個；(2) 「增量段本身乾淨」不代表「adopt 前的既有內容沒有
  問題」——如果 adopt 前的內容本身有 bug 或違反 scope，只審增量段會
  完全漏檢，這正是 continuation 這個功能存在的初衷（"以完成既有 diff
  為完成定義"）與「exact-candidate 純度」的審查完整性两个目标产生真实
  衝突的地方，不是工程細節問題，是產品／風險政策問題。

**本文明確不替 maintainer 決定**——這是全篇設計中風險係數最高的單一
決策點，選 (a) 還是 (b)、抑或某種混合（例如 (a) 但對 continuation
candidate 額外要求 adversarial-review 强制掛載，不管 band 為何，比照
`mcu-feature` combo 對硬體證據類任務的既有先例）都合理，取決於
maintainer 對「adopt 既有未受監督內容」的風險胃納。

### D6 治理骨架：沿用既有 7-phase combo，不新增更輕量 combo、不跳過 planning／review phase

**決策**：比照 `openspec/changes/2026-08-07-design-adhoc-oneshot-dispatch`
D3 的既有立場——continuation slice 沿用受 `validate_manager_spine()` 七
phase 涵蓋、persona 綁定、ship-前-reviewer 三條治理憲法管轄的既有 combo
骨架（`small-fix` 或 `feature-oneshot`，依任務規模由操作者選擇），不新增
更輕量的 combo，不跳過 planning 或 review phase。

理由：continuation 的訴求是「不必照 plan 從頭實作」，不是「不需要治理」——
issue 型 1／2 描述的既有 diff 規模（15+ 檔案）與型 3 的多分支合併衝突，
恰恰是最需要 review 把關的情境，不是應該被豁免 review 的情境。planning
phase 的產出從「凍結實作步驟的 plan」改為「continuation brief」（描述
adopt 的既有狀態是什麼、還缺什麼才算完成、預期 gate）——這比照 #279 D3
「把 `--prompt-file` 內容當 `brainstorming`／`writing-plans-light` 兩張
卡的輸入 brief」的既有設計立場，不是本文首創。

build phase 的 dispatch prompt 改走 continuation-aware 模板：偵測到
`mid_merge.detect_merge_state().in_progress` 時嵌入衝突檔案清單與「完成
merge、禁止 abort」指示（D4）；`mode=adopt-worktree` 且 `adopt_dirty`
時嵌入「這是既有未完成的工作，你的任務是完成它，不是重新開始」的明確
指示，防止 builder session 誤判成「這個 worktree 壞了，我應該清空重來」
（這是一個真實的行為風險：若 prompt 沒有明確說明 worktree 現況是預期
中的既有工作，通用 coding agent 遇到 dirty worktree 的常見反應是先
`git stash` 或 `git checkout .` 清空後重新開始，這正好是 continuation
最不想要的結果）。prompt 模板擴充方式比照
`openspec/changes/2026-08-07-builder-task-boundary-segmentation` D3 的
`build_dispatch_prompt()` 新增 optional `task_slice` 參數、未傳維持既有
行為不變的既有先例——不新增卡片，不新增 combo。

### D7 完成定義：重用既有 verification 契約（查證更正 issue 假設），零 commit 情境未決

**決策**：直接回應 issue 建議「完成定義改可宣告式 gate（測試命令＋乾淨
working tree＋commit 存在）」——查證確認這已經是既有
`validate_verification_contract()`（`verification.py:207-303`）的
`tests`／`full_suite` 欄位＋`run_result_verification()` 既有的
`candidate-worktree-dirty`（712-726 行）／`candidate-not-advanced`
（727-728 行）兩項檢查逐字提供的能力。continuation **不需要**新增
任何 gate schema，直接沿用。這是本設計比照 #279 對 #338 的「查證更正
issue 假設」同類型發現——issue 作者當下對現有能力的認知有落差，設計
文件的職責之一是核對並更正，不是照單全收字面建議。

**未決（本文不裁定）**：型 4「純驗證＋簽核」情境——既有 diff 已經是
操作者認為完成的最終狀態，continuation build phase 唯一該做的事是驗證
（跑測試、確認乾淨）並視結果簽核，理論上可能**零新 commit**。這與現行
`candidate-not-advanced` 不變量（candidate 必須異於 dispatch base）直接
衝突。兩個選項：

- 一律要求至少一個 commit（即使是 `git commit --allow-empty` 的 no-op
  簽核 commit）——不需要修改 `run_result_verification` 任何一行，把
  「零新 commit」重新定義為「以一個空 commit 明確標記『我（cortex）已
  驗證此狀態並簽核完成』」，這個空 commit 本身就是一種可稽核的簽核
  紀錄。
- 為 `candidate-not-advanced` 開一個顯式 opt-out（例如 verification
  契約新增 `allow_zero_new_commits: true`），讓「真的零變更」的情境
  合法通過。

前者不需要碰任何既有不變量、且額外帶來「簽核有明確 commit 紀錄」的
副作用（可能是優點），是本文傾向但不擅自拍板的選項；後者更貼合「零
變更」的字面語意，但打開了一個新的 opt-out 分支，需要新增測試涵蓋
「濫用 opt-out 掩蓋真正該有變更卻沒做」的反例。留待 maintainer 決定。

### D8 GC／生命週期邊界：確認既有機制已足夠，非新增行為

**現況查證**：`gc.py::scan()`（281-303 行）：

```python
pool_root = (worktree_root if worktree_root is not None else worktree_root_for(repo_root)).resolve()
...
for entry in list_worktrees(repo_root, git_runner):
    ...
    if not _is_under(resolved, pool_root):
        continue
```

第 302 行的 `_is_under` 邊界檢查已經排除任何不在 `worktree_root` pool
內的 worktree——adoption 使用的操作者本地路徑（issue 描述的
"lane worktree"）幾乎必然落在 pool 之外，天然被排除於 GC 掃描範圍。
即使 adopted worktree 恰好落在 pool 內（例如操作者沿用了 cortex 自己的
worktree 命名慣例），`_classify_worktree()`（226-258 行）對 dirty
worktree 一律回傳 `KEEP`／`REASON_DIRTY_WORKTREE`（244-245 行），
在整個 continuation 進行期間天然保護，不需要額外邏輯。

**決策**：確認、不變更——`gc.py` 不需要為 continuation 修改任何一行。
唯一需要在後續實作票留意的：continuation slice 完成後，若 job 的
`worktree` 欄位指向的是 adopted 外部路徑，`cortex work gc` 依然不會
主動清理它（不論是否落在 pool 內，dirty 時保護、clean-and-merged 時
即使落在 pool 內被 reclaim 也是合理的既有行為，等同任何其他完成
slice）——這與型 3／4「操作者自行管理續作分支的生命週期」的預期一致，
不需要新增排除清單或標記欄位。

## 風險與緩解

- **風險：adoption 的 branch 命名脫離 `feature/<slice_id>` 慣例，可能
  與既有工具（`cortex inspect status`、GC 分類）對 branch 名稱格式的
  隱性假設衝突**。緩解：D2 已明確要求四處 `_branch_for_slice()` 呼叫點
  在 continuation 路徑改讀 spec 宣告值；後續實作票驗收 MUST 包含對
  `cortex inspect status`／`gc.py` 消費任意 branch 名稱（非
  `feature/*` 格式）的回歸測試，不能假設所有既有消費端都已對非慣例
  命名安全。
- **風險：`adopt-branch` 模式若目標 branch 當下被操作者自己的主要
  checkout 佔用，`git worktree add` 會直接失敗**。緩解：D2 已明確
  這是 git 本身的不變量、非本設計新增的限制，fail-closed 並回傳原始
  git 錯誤訊息即可，不需要額外的「自動切換操作者工作目錄」邏輯（那會
  是一個更高風險、职责邊界不清的功能，本文明確不做）。
- **風險：型 3「已完成未併入的 lane 分支序列合併」若操作者誤期待
  cortex 能自動決定合併順序、自動處理跨分支衝突**。緩解：本文明確
  這不是 v1 範圍——型 3 建議的落地方式是操作者逐一宣告多個
  continuation slice，以既有 `depends_on` 機制鏈接（例如 slice B
  `depends_on: [slice-A]`，等 A 完成後才輪到 B 的 adoption），序列
  順序仍由操作者決定，cortex 不做任何自動排序或衝突預測。若後續證明
  這個模式不夠用，需要獨立立案評估專屬的多分支合併原語，不與本票的
  v1 範圍捆綁。
- **風險：D5／D7 的未決問題若被後續實作票的執行者自行拍板，會架空
  本文刻意保留給 maintainer 的決策空間**。緩解：`tasks.md` 已明確
  標示這兩項為「本票不替 maintainer 決定」且列入「後續應拆分的 code
  票」的獨立佔位項（依賴 maintainer 決策，不預先假設答案），任何後續
  票若要落地 D5／D7 相關程式碼，PR 描述應明確引用 maintainer 對應本
  段落的實際決策紀錄（例如 issue comment 或另一份決策 ADR），而非直接
  動手实作其中一個選項。

## 未決問題總覽（需 maintainer 拍板，本票不擅自決定）

1. **D5：continuation candidate 的審查範疇**——ForeignReview／
   `verification.checks` 應評估 `dispatch_base..candidate` 全段（含
   adopt 前既有內容），還是只評估 adopt 後的增量段（需新增第二
   baseline）？兩者代價已在 D5 完整列出。
2. **D7：零新 commit 情境**——型 4「純驗證＋簽核」若真的零變更，是
   要求至少一個 no-op 簽核 commit（不改動任何既有不變量），還是為
   `candidate-not-advanced` 開一個顯式 opt-out？
3. **（附論，優先度較低）型 3 的多分支序列合併**——本文建議以既有
   `depends_on` 鏈接多個 continuation slice 因應，但若實務上序列規模
   大、衝突複雜到需要更聰明的自動化輔助（例如自動偵測衝突集中的核心
   檔案、建議合併順序），是否值得開一張獨立設計票，還是维持操作者
   手動決定順序即可？本文傾向後者（避免過度設計一個尚無實測需求規模
   佐證的功能），但這是可以隨時間累積更多實際案例後再重新評估的
   決定，不急於本票拍板。
