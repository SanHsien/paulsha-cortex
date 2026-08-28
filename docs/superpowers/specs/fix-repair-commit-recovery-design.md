---
status: accepted
work_item: fix-repair-commit-recovery
---

# fix-repair-commit-recovery Design

## Decisions

### D1 新增獨立窄化 action，不放寬 retry-build 的 CAS

以 `_recover_planning_action` 為模板（`_recover_pre_candidate_action` 為第二個先例）新增 `_recover_repair_commit_action`；`_retry_build_action` 的 `expected_candidate` exact CAS 與 `_manager_reset_workflow_for_retry_build` 的 exited/0 unbound 窄化入口原封不動。

理由：issue #260 的 2026-08-01 複驗結論明確要求沿用既有恢復動作的形狀而非另立一套，也明確要求不得放寬既有關卡。放寬 retry-build 的 admission 會讓「失敗 job 的 worktree 內容」在沒有 operator 明確指認 SHA 的情況下取得重派資格，模糊 CAS 的責任邊界；獨立 action 讓「adopt 既有 commit」與「重派新 builder」是兩個語意分離、各自 fail-closed 的入口。

### D2 判準全部取自系統事實，caller 參數只做交叉比對

worktree 路徑取自 failed builder job row；HEAD、乾淨度、descendant lineage 全部由 manager 側 git 呼叫確認（沿用 `_verify_exact_candidate`／`_verify_build_candidate_transition` 的驗證語意）；operator 提供的 `expected_run_id` 與 `expected_candidate` 只用來與系統事實交叉比對，白名單外參數一律拒絕。

理由：這是 `recover-planning`／`recover-pre-candidate` 已確立的模式——caller 帶的內容永遠不成為 evidence。操作面上 operator 仍必須明確指認要 adopt 的 SHA（對應 issue 期望行為「要求 operator 提供 exact expected SHA」），但授權判準的每一項都能被系統獨立重算，錯誤的指認只會 fail closed，不會 bind 錯 commit。

### D3 adoption 以 manager 登錄的 adoption job row 承載觀測事實

adoption 成功時登錄一筆新 job row：欄位沿用既有 job row 欄位集合（不新增欄位），identity、worktree、dispatch_head 複製自 failed job，`subject_head` 為 adopted candidate，狀態 exited/0，`workflow_evidence` 指向 adoption record；failed job 原始 row 原樣保留。provenance（failed job id、observed HEAD、失敗原因）記錄在 adoption evidence record 內，不新增 job row 欄位。

理由：下游的 `_verify_exact_candidate` 與 `_review_builder_job_binding` 都要求「一筆 exited/0、subject_head 等於 candidate 的 builder job」才能繼續 verify／exact-head review。與其放寬這兩個 binding（會弱化所有 run 的驗證強度），不如補一筆完整通過驗證的事實紀錄——row 上每個欄位都是 manager 確定性驗證過的 git／registry 事實。不新增欄位是 #205 的教訓：新欄位落在 providers 投影白名單之外會讓整份 projection 變 degraded。改寫 failed job row 則違反 job 紀錄不可變原則，故不採用。

### D4 evidence record 與 CAS 冪等，比照 recover-planning 的 already-recovered 模式

adoption 寫入 `cortex-work-repair-adoption/v1` durable record（`evidence/work-repair-adoption/<run_id>-<digest>.json`，digest 取 canonical JSON hash，比照 `_abandon_record`）。重送相同 request 時，若 run 的 `candidate_head` 已是 expected SHA 且對應 record 存在，直接回 `already-recovered`，不做任何第二次變更。

理由：`recover-planning` 已用「掃描既有 recovery evidence → already-recovered」實現冪等，同一模式讓 operator 與 auto-run 重送 request 時天然安全（對應 issue 期望行為「同一 recovery request 不得重複啟動 model session」——本 action 更進一步：任何情況都不啟動 model session）。CAS 失敗（run 已前進到其他 candidate）則 fail closed，不做模糊比對。

### D5 registry 原子方法完成 bind 與 phase 前進

新增 `_manager_adopt_repair_candidate`（`paulsha_cortex/coordinator/registry.py`），比照 `_manager_reset_workflow_for_retry_build` 的 CAS／admission 風格：驗 run 狀態、final build card pending、無 active job 後，在單一 persist 內完成——`candidate_head` 更新為 adopted SHA、final build step 以 adoption job 的 builder identity 標 passed、`current_phase` 進 verify、`attempts["verify"]` 遞增、移除 `needs_human` facet、`verified_head` 歸零、evidence_refs 附掛 adoption record。

理由：分散多次 update 會產生「candidate 已換但 card 還 pending」的 crash window，dispatch 可能在中間狀態重派 builder。registry 既有的 retry reset 方法都是單一原子 persist，adoption 沿用同一風格。build step 用 builder identity（複製自 failed job）而非 manager identity 標 passed，是為了讓 review phase 的 foreign-domain 檢查（builder_domains 取自 build steps）對照的是真正寫出 commit 的 builder domain。

### D6 resume／dispatch 的 failed terminal 判定補上 exited 非 0

`resume_workflow_run` 的 replacement 判定與 `_dispatch_workflow_card` 的 `retryable_latest` 判定，在 retry_failed 情境下把「`status == "exited"` 且 exit code 非 0」視同 `status == "failed"`（對齊 `TERMINAL_STATUSES` 的終止語意）；exited/0 的路徑（unbound terminal、malformed schema retry）原封不動。失敗回報附掛 `_terminal_parse_diagnostics` 唯讀診斷。

理由：兩處判定目前只認 `status == "failed"`，exited 非 0 的 stale terminal 會讓第一次 resume 空轉一輪（重新回報 job-failed、重掛 needs_human），第二次才 dispatch replacement——這正是 issue 複驗指出「仍未處理」的第三項。收斂點選在既有條件式，不另立選擇機制，改動面最小；診斷與授權分離沿用 #261 的 `authority_granted: false` 模型，可觀測不等於可授權。

## 風險與緩解

- **adoption job row 被誤讀為正常成功的 builder job**：row 的 `workflow_evidence` 指向 `cortex-work-repair-adoption/v1` record，record 內含 failed job id 與失敗原因，稽核可完整還原「誰失敗、誰採納、採納了什麼」；且 verify／review 仍會對 adopted candidate 完整重新把關，adoption 不授予任何品質判定。
- **新欄位造成 Monitor 投影 degraded（#205 曾實際踩到）**：adoption job row 與 WorkflowRun 更新都只使用既有欄位；provenance 一律放 evidence record。測試以 providers 投影非 degraded 作為驗收之一。
- **resume 條件變更影響既有 malformed-terminal／schema-retry 路徑**：擴充嚴格限定在「exit code 非 0 的 exited terminal」，exited/0 的三條既有路徑（unbound terminal recovery、malformed schema retry、正常 terminalize）條件式不動；以回歸測試鎖定 `test_resume_replay_keeps_single_replacement_job` 與既有 schema-retry 測試全綠。
- **worktree 在 adoption 前被回收或改動**：所有 git 事實在 action 執行當下重新驗證，worktree 缺失、dirty、HEAD 不符即 fail closed；此時 operator 仍可改走既有 `retry-build`（重派新 builder session），不會卡死。
- **adoption 與 retry-build 對 exited/0 unbound 情境重疊**：屬刻意設計——該情境兩個入口都合法（adopt 不花 model session、retry-build 重派修復），由 operator 依 commit 是否可信選擇；兩者 CAS 各自獨立，不互相放寬。
