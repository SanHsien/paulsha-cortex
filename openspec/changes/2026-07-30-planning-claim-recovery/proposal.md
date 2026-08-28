---
status: accepted
work_item: planning-claim-recovery
---

## Goals

讓「在壞環境下 claim 過一次」的 work item 可以在環境修好後前向恢復，並讓 abandon 真正釋放 work item 而非卡成另一種永久死。

## Why

planning runtime 只在 claim 當下執行一次，事後修好環境也救不回來；四個恢復桿實測全部無效，唯一出口 abandon 會讓 work item 卡在 blocked 且 start／resume 全部短路在 persisted-block。觸發器已由 #255 修復，但一次性 planning 執行加上無前向恢復這個核心缺陷仍在。

## What Changes

- 在 run 的 planning 失敗記錄中保留可機械判定的原因分類（環境面 vs 內容面），恢復動作依分類放行或拒絕。
- 新增 work action 重跑 planning，run identity 與 authority 凍結不變；要求 `expected_run_id`（CAS）且具冪等性。
- `_resume_decision` 對 `needs_human` 改回傳帶 reason 與 `next_actions` 的結構化結果。
- abandon 寫入可辨識的釋放標記，claim 路徑據此允許同識別重新 claim；釋放標記只對新的 abandon 寫入，不回溯改變既有 blocked run。

## Capabilities

### Modified Capabilities
- 詳見 `docs/superpowers/specs/planning-claim-recovery-spec.md` 的 Requirements 與 `docs/superpowers/specs/planning-claim-recovery-design.md` 的 Decisions。
