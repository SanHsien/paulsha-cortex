---
status: accepted
work_item: fix-repair-commit-recovery
---

## ADDED Requirements

### Requirement: repair commit 缺 terminal evidence 時必須有窄化 adoption 出口

repair job 失敗終止（`status == "failed"`、exited 且 exit code 非 0，或 exited/0 但 terminal payload 缺漏／malformed）而其 worktree 留有合法 descendant commit 時，Manager MUST 提供獨立的 `recover-repair-commit` action 將該 commit 確定性地 bind 為新 candidate。此 action MUST 只在 run 為 ongoing、帶 `needs_human`、停在 build phase、前置 build card 全 passed、final builder card pending、最新同 card job 無 bound `workflow_evidence` 且無 active job 時可用，且 MUST NOT 啟動任何 model session。

#### Scenario: failed repair job 留下 descendant commit

- **WHEN** repair job 以非 0 exit code 終止、無 terminal evidence，worktree HEAD 為原 candidate 的 descendant，operator 以 exact run id 與 exact SHA 執行 `recover-repair-commit`
- **THEN** run 的 `candidate_head` 更新為該 SHA、final build card 標 passed、run 進入 verify phase
- **THEN** 產生 `cortex-work-repair-adoption/v1` durable evidence record，且未啟動任何 model session

#### Scenario: evidence 已 bind 時拒絕

- **WHEN** 最新同 card builder job 已有 bound `workflow_evidence`
- **THEN** `recover-repair-commit` fail closed 並回報具體原因，run 狀態不變

### Requirement: adoption 判準必須取自系統可驗證的事實

`recover-repair-commit` 的驗證輸入 MUST 取自系統既有紀錄與 git 事實：worktree 路徑 MUST 取自 failed builder job row；operator 提供的 `expected_candidate` MUST 精確等於該 worktree HEAD；worktree MUST 乾淨；`expected_candidate` MUST 為原 candidate 的合法 descendant 且不得與其相同；issue MUST 經 WorkAuthority 授權。caller 參數 MUST 只做交叉比對、MUST NOT 被當作 evidence 採信；白名單外參數 MUST 拒絕。任一判準不符 MUST fail closed。

#### Scenario: 非 descendant 拒絕

- **WHEN** operator 提供的 SHA 不是原 candidate 的合法 descendant
- **THEN** fail closed 並回報具體原因，candidate authority 不變

#### Scenario: dirty worktree 拒絕

- **WHEN** failed job 的 worktree 有未 commit 的變更
- **THEN** fail closed 並回報具體原因，不 bind 任何 candidate

### Requirement: adoption 必須具 CAS 冪等且不放寬既有關卡

`recover-repair-commit` MUST 要求 `expected_run_id` 與 `expected_candidate` 雙重 CAS；重送相同 request MUST 回報 `already-recovered`，MUST NOT 產生第二次 adoption、第二個 job row 或任何 model session。`retry-build` 的 exact `expected_candidate` CAS 與既有 exited/0 unbound terminal 窄化入口 MUST 保持原封不動。

#### Scenario: 重送相同 request

- **WHEN** adoption 成功後 operator 重送相同的 `recover-repair-commit` request
- **THEN** 回報 `already-recovered`，job 總數與 evidence record 數不變

#### Scenario: retry-build CAS 不放寬

- **WHEN** `retry-build` 未提供 `expected_candidate` 或 SHA 與 `candidate_head` 不符
- **THEN** 以與現況一致的錯誤 fail closed，admission 未因新 action 放寬

### Requirement: adoption 後生命週期必須可續行且可稽核

adoption 成功後，run MUST 進入 verify phase，既有 verify → foreign review → exact-head final 管線 MUST 以 adopted candidate 重新把關，MUST NOT 重跑已完成的 planning。adoption MUST 登錄一筆沿用既有欄位集合的 adoption job row（identity 複製自 failed job、`subject_head` 為 adopted SHA、exited/0、`workflow_evidence` 指向 adoption record），使既有 builder job binding 驗證不需放寬；failed job 原始 row MUST 原樣保留；provenance（failed job id、observed HEAD、失敗原因）MUST 記錄於 adoption evidence record。

#### Scenario: adoption 後繼續 exact-head review

- **WHEN** adoption 完成後 workflow 繼續推進
- **THEN** verify 與 foreign review 對 adopted candidate 完整重新把關，reviewer 可 bind 到 adoption job row 的 worktree 與 exact HEAD

### Requirement: resume 不得重選 stale failed job

`resume`／`retry-build` 的 job 選擇 MUST 選擇最新且符合 run／action 的 eligible job。operator resume 遇到已 terminalized 的失敗 job（`status == "failed"`，或 exited 且 exit code 非 0）時，第一次 resume MUST 即 dispatch replacement job，MUST NOT 先重選 stale failed job；replacement 在飛行中時再次 resume MUST 回報 in-flight 且 MUST NOT 產生第二個 replacement job。失敗回報 MUST 附帶唯讀 terminal 診斷（observed HEAD、job id、失敗原因），且 MUST NOT 因此授予 candidate authority。

#### Scenario: 第一次 resume 即 dispatch replacement

- **WHEN** 最新同 card job 為 exited 且 exit code 非 0 的 stale terminal，operator 執行第一次 `resume`
- **THEN** Manager dispatch replacement job，不重新回報 stale job 的失敗

#### Scenario: 重送 resume 不產生第二個 replacement

- **WHEN** replacement job 仍在飛行中，operator 再次執行 `resume`
- **THEN** 回報 in-flight，job 總數不變
