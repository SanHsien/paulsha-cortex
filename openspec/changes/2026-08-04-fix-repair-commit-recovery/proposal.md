---
status: accepted
work_item: fix-repair-commit-recovery
---

## Goals

repair commit 已在 worktree 但缺 terminal evidence 時，提供具 CAS 的窄化 `recover-repair-commit` 動作將其確定性地 bind 為新 candidate，並修正 resume／retry-build 的 job 選擇不再重選 stale failed job，讓 auto-run 修復迴路可自行閉環（#260）。

## Why

repair job 失敗終止但已在 builder worktree 產生合法 descendant commit 時，`retry-build` 的窄化入口只接受 exited/0 的 unbound terminal builder job，可驗證的修復 commit 無法被 bind、驗證或繼續 exact-head review；同時 `resume` 對 exited 非 0 的 stale terminal job 會先空轉一輪重新回報失敗，第二次才 dispatch replacement。operator 只能介入 runtime state，auto-run 無法閉環。近期落地的 `recover-planning`（#256）與 `recover-pre-candidate`／dirty candidate 重評（#277）情境各不相同，均未涵蓋此缺口。

## What Changes

- 新增獨立窄化 `recover-repair-commit` work action（模板：`_recover_planning_action`／`_recover_pre_candidate_action`）：`expected_run_id` 與 `expected_candidate` 雙 CAS；判準全部取自系統事實（worktree 取自 failed job row、HEAD 精確比對、乾淨度、descendant lineage、authority），caller 參數只做交叉比對；不啟動任何 model session。
- adoption 產生 `cortex-work-repair-adoption/v1` durable evidence record 與一筆沿用既有欄位集合的 adoption job row（identity 複製自 failed job、subject_head 為 adopted SHA、exited/0、workflow_evidence 指向 record），failed job row 原樣保留；registry 以原子方法完成 candidate bind、final build card 標 passed 與 verify phase 前進。
- 冪等：重送相同 request 回 `already-recovered`，不產生第二次 adoption、第二個 job row 或 model session。
- `retry-build` 的 exact expected_candidate CAS 與既有 exited/0 窄化入口原封不動；最新 job 已有 bound evidence 時 `recover-repair-commit` 拒絕。
- `resume_workflow_run`／`_dispatch_workflow_card` 的 failed terminal 判定補上「exited 且 exit code 非 0」，第一次 operator resume 即 dispatch replacement；失敗回報附掛唯讀 terminal 診斷（不授予 authority）。
- control queue 白名單、`cortex work`／`cortex recover work` CLI surface 與 `docs/unified-work-lifecycle.md` 同步。

## Capabilities

### Modified Capabilities

- `persona-workflow-orchestration`：詳見 `docs/superpowers/specs/fix-repair-commit-recovery-spec.md` 的 Requirements 與 `docs/superpowers/specs/fix-repair-commit-recovery-design.md` 的 Decisions。
