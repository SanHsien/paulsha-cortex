---
status: accepted
work_item: per-work-model-chain
---

# per-work-model-chain Specification

#205：支援 per-work 的 planner → builder → reviewer 模型鏈覆寫，讓單一 WorkItem 可精確指定並稽核模型鏈，而不必更動共享 registry 順序影響其他 active run。

## 背景

以 canonical Work lifecycle 驗證派工時，operator 需要為單一 WorkItem 精確指定 planner → builder → reviewer 的模型鏈，並能從 durable evidence 稽核實際解析結果。

目前只能調整共享的 `model-identities.yaml` 順序，而這會影響其他 active run 尚未派出的 workflow card：`cortex run work start/resume/retry-build/ship` 沒有 run-scoped 的 `--model`／`--review-model` 覆寫，現有 `--model` 只接在 legacy `tick`／`fanout` 路徑；canonical card 由 `_select_workflow_identity` 依 capability 過濾後取第一個 candidate，而 custom identities 會排在 packaged identities 之前。

因此為了 dogfood 特定模型而改共享 registry，會干擾同時執行的其他工作；resume／retry 若重新依共享 registry 選擇，也可能與首次 dispatch 的 operator 意圖漂移。

## Goals

- 單一 WorkItem 的三段模型鏈可被隔離指定、凍結並稽核。
- 為特定 work 指定模型不影響其他 active run。
- resume／retry 沿用首次 dispatch 的意圖，不因共享 registry 變動而漂移。

## Requirements

### R1 run-scoped 模型鏈覆寫

`cortex work` 的相關動作 SHALL 支援 run-scoped 的模型鏈覆寫，至少可分別指定 planner、builder、reviewer 的 executor 與 model。

覆寫 MUST 只作用於該 run，MUST NOT 改變共享 `model-identities.yaml`，也 MUST NOT 影響其他 active run 尚未派出的 card。

### R2 覆寫在 claim 時凍結

覆寫值 SHALL 於 claim（或首次 dispatch）時凍結進 run 記錄。

後續 resume／retry-build／retry-verify／retry-review MUST 沿用凍結值，MUST NOT 重新依共享 registry 選擇，除非 operator 明確再次覆寫。

### R3 覆寫仍受既有約束

覆寫指定的 identity MUST 通過既有 capability 檢查；builder 與 reviewer 的 `independence_domain` MUST NOT 相同。

指定不存在或不符約束的 identity 時 MUST fail closed 並回報具體原因，MUST NOT 靜默退回共享 registry 的預設選擇。

### R4 解析結果可稽核

run 的 durable evidence MUST 記錄三段各自實際解析到的 executor、model 與來源（run-scoped 覆寫 vs 共享 registry），使事後可稽核「這次到底用了什麼模型、為什麼」。

## 非目標

- 不改共享 registry 的既有選擇演算法（capability 過濾後取第一個 candidate 的行為維持）。
- 不改 identity probe 邏輯（#255 已修）。
- 不實作 capability-based 自動路由（屬 #209 範圍）。

## 驗收面

- 可為單一 WorkItem 指定三段模型鏈，且不影響其他 active run。
- 覆寫值於 claim 時凍結，resume／retry 沿用而不漂移。
- 覆寫不通過 capability 或 independence domain 檢查時 fail closed 並回報原因。
- durable evidence 記錄三段實際解析結果與其來源。
