---
status: accepted
work_item: fix-repair-commit-recovery
---

# fix-repair-commit-recovery Specification

#260：repair commit 已在 worktree 但缺 terminal evidence 時，提供具 CAS 的窄化 adopt/recover 動作，並修正 resume／retry-build 不再重選 stale failed job，讓 auto-run 修復迴路可自行閉環。

## 背景

以 Cortex auto-run dogfood 修復迴路時重現一條沒有 recovery path 的狀態：原 candidate 經對抗審查拒絕後，repair worker 在既有 builder worktree 產生新的 descendant commit，但 repair job 隨後以失敗終止、沒有留下可採用的 terminal evidence。

現況有兩個缺口。第一，admission 缺口：`_manager_reset_workflow_for_retry_build`（`paulsha_cortex/coordinator/registry.py`）的 build phase 窄化入口只接受 `status == "exited"` 且 `exit_code == 0` 的 unbound terminal builder job，真正的 failed job（`status == "failed"` 或 exited 非 0）即使 git object 與 worktree HEAD 均存在也無法被 adopt；`_classify_retry`（`paulsha_cortex/coordinator/work_actions.py`）的 `terminal_with_evidence` 篩選同樣要求 `exit_code == 0`。第二，選擇缺口：`resume_workflow_run`（`paulsha_cortex/coordinator/manager.py`）的 replacement 判定只認 `status == "failed"`，對 `status == "exited"` 且 exit code 非 0 的 stale terminal job，第一次 resume 只會重新回報 `job-failed` 並重掛 needs_human，要再執行一次才 dispatch replacement。

結果是可驗證的修復 commit 已存在，但 lifecycle 無法安全地 bind、驗證或繼續 exact-head review，operator 只能介入 runtime state。

近期已落地的 `recover-planning`（#256）、`recover-pre-candidate` 與 dirty candidate 重評（#277／PR #290）同屬「lifecycle 卡死無出口」家族但情境各不相同：前者發生在 build 之前、與 candidate 無關；`recover-pre-candidate` 處理的是**沒有** commit 可 adopt 的情況；dirty candidate 重評是重跑 verification 重新判定。三者都沒有涵蓋本 work item 的核心——repair job 失敗終止、但已產生可驗證的 descendant commit。#292（機械驗收，PR #293）屬 quality 模組，與本缺口無關。

## Goals

- repair job 即使 process／terminal 失敗，也不默默遺失已產生 candidate 的可觀測性與可恢復性。
- manager 在 fail-closed 前提下，對既有 repaired HEAD 提供明確、具 CAS 的 recovery action，通過確定性驗證後 bind 為新 candidate。
- resume／retry-build 選擇最新且符合 run／action 的 eligible job，第一次 resume 即 dispatch replacement，不重選已 terminalized 的 stale failed job。
- 同一 recovery request 具冪等性，不重複啟動 model session。

## Requirements

### R1 獨立窄化 recovery action

系統 SHALL 新增獨立的 `recover-repair-commit` work action，比照 `_recover_planning_action`／`_recover_pre_candidate_action`（`paulsha_cortex/coordinator/work_actions.py`）的既有模式實作。

此 action MUST 只在下列全部條件成立時可用，任一不成立 MUST fail closed 並回報具體原因：

- WorkflowRun 為 ongoing、帶 `needs_human` facet、`current_phase == "build"`。
- 前置 build card 全部 passed、final builder card 為 pending。
- 最新同 card builder job 為失敗終止（`status == "failed"`，或 `status == "exited"` 且 exit code 非 0，或 exited/0 但 terminal payload 缺漏／malformed），且其 `workflow_evidence` 為 `None`。
- 該 run 無任何 active（in-flight）workflow job。

此 action MUST NOT 啟動任何 model session——adoption 完全由 manager 側確定性驗證完成。

### R2 判準取自系統可驗證的事實

recovery 的驗證輸入 MUST 取自系統既有紀錄與 git 事實，caller 帶的參數只做交叉比對、MUST NOT 被當作 evidence 採信：

- worktree 路徑 MUST 取自 failed builder job row，不接受 caller 指定路徑。
- operator 提供的 `expected_candidate`（40-hex exact SHA）MUST 精確等於該 worktree 的 `git rev-parse HEAD`。
- 該 worktree MUST 乾淨（`git status --porcelain` 為空）；dirty worktree MUST 拒絕。
- `expected_candidate` MUST 為原 candidate（`run.candidate_head`）的合法 descendant（`git merge-base --is-ancestor` 成立），且 MUST NOT 與原 candidate 相同——相同時代表沒有新 commit 可 adopt，MUST 拒絕並提示改走 `retry-verify`。
- `--issue` 有指定時 MUST 屬於 WorkAuthority 的 mapped issues；run 的 issue_refs／openspec_refs MUST 與 authority 一致。
- 白名單以外的 caller 參數 MUST 拒絕（比照既有 `rejects caller evidence/input` 模式）。

### R3 CAS 與冪等性

此 action MUST 要求 `expected_run_id`（`workflow-[0-9a-f]{20}` exact match）與 `expected_candidate` 雙重 CAS。

adoption 成功後 MUST 產生 durable evidence record（schema `cortex-work-repair-adoption/v1`，存於 coordinator state 的 `evidence/work-repair-adoption/` 下），記錄 failed job id、observed HEAD、adopted candidate、previous candidate 與 actor。

重送相同 request 時，若該 run 已存在對應的 adoption record 且 candidate 已前進，MUST 回報 `already-recovered` 且 MUST NOT 產生第二次 adoption、第二個 job row 或任何 model session。

### R4 不放寬既有關卡

`retry-build` 的 `expected_candidate` exact CAS（`paulsha_cortex/coordinator/work_actions.py` 的 `_retry_build_action`）MUST 保持原封不動；`retry-verify`／`retry-review` 的 CAS 與 admission 同樣不變。

`recover-repair-commit` MUST NOT 成為繞過 terminalization 或 gate 驗證的後門：最新同 card job 已有 bound `workflow_evidence` 時 MUST 拒絕；`_manager_reset_workflow_for_retry_build` 既有的 exited/0 unbound 窄化入口行為 MUST 保持不變。

### R5 adoption 後生命週期可續行

adoption 成功後，run 的 `candidate_head` MUST 更新為 adopted candidate，final build card MUST 以確定性方式標為 passed，run MUST 進入 verify phase；既有 verify → foreign review → exact-head final 管線 MUST 以 adopted candidate 重新把關內容品質，MUST NOT 重跑已完成的 planning。

為使既有 verify／review 的 builder job binding（`_review_builder_job_binding`、`_verify_exact_candidate`，`paulsha_cortex/coordinator/manager.py`）不需放寬，adoption MUST 登錄一筆 manager 記錄的 adoption job row：欄位沿用既有 job row 欄位集合（不新增欄位），identity（executor／model／independence_domain）、worktree 與 dispatch_head 複製自 failed job，`subject_head` 為 adopted candidate，`status`/`exit_code` 為 exited/0，`workflow_evidence` 指向 adoption record。failed job 的原始 row MUST 原樣保留不得改寫。

### R6 resume／retry-build 不重選 stale failed job

`resume_workflow_run` 與 `_dispatch_workflow_card`（`paulsha_cortex/coordinator/manager.py`）在 operator resume（retry_failed）情境下，對「已 terminalized 的失敗 job」的判定 MUST 涵蓋 `status == "exited"` 且 exit code 非 0 的情況（與既有 `status == "failed"` 並列），使第一次 resume 即 dispatch replacement job，MUST NOT 先重選 stale failed job 空轉一輪。

replacement dispatch 後再次 resume MUST NOT 產生第二個 replacement job（in-flight job 存在時回報 in-flight）。

resume 對失敗 job 的回報 MUST 附帶唯讀 terminal 診斷（沿用 #261 的 `_terminal_parse_diagnostics`：observed HEAD、job id、失敗原因），且 MUST NOT 因此授予任何 candidate authority。

## 非目標

- 不放寬 `retry-build`／`retry-verify`／`retry-review` 的 CAS 與 admission（R4 明確鎖定）。
- 不改 gate ledger／terminal contract 本身（#261 已定案；本 work item 只引用其 evidence 驗證模式）。
- 不涵蓋 slice lane 的 pre-candidate 恢復與 dirty candidate 重評（#277／PR #290 已落地）。
- 不提供自動 adoption——periodic runner 不取得此 recovery authority，沿用既有 operator-only recovery 原則。
- 不處理 malformed passed-terminal／null candidate（#106）與 slice failed state 無 action（#153）的既有範圍。

## 驗收面

- 測試重現 repair job 留下 descendant commit、exit 非 0／terminal missing 的情境，並可經 `recover-repair-commit` 恢復後繼續 verify → foreign review → exact-head final。
- 非 descendant、dirty worktree、evidence 已 bind、issue 未授權時全部 fail closed 並回報具體原因。
- 第一次 operator resume 即 dispatch replacement，不重選 stale failed job；重送相同 request 不產生第二個 replacement job 或第二次 adoption。
- `retry-build` 的 exact expected_candidate CAS 行為與現況完全一致（回歸測試鎖定）。
- 狀態面可見 observed worktree HEAD、job id、失敗原因，但未通過驗證前不授予 candidate authority。
- operator 文件（`docs/unified-work-lifecycle.md`）與 CLI help 同步更新。
