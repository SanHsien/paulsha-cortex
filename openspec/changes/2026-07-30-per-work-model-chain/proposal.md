---
status: accepted
work_item: per-work-model-chain
---

## Goals

支援 per-work 的 planner → builder → reviewer 模型鏈覆寫，讓單一 WorkItem 可精確指定並稽核模型鏈，而不必更動共享 registry 順序影響其他 active run。

## Why

目前只能調整共享 `model-identities.yaml` 順序，這會影響其他 active run 尚未派出的 card；resume／retry 若重新依共享 registry 選擇，也可能與首次 dispatch 的 operator 意圖漂移。

## What Changes

- WorkflowRun 增加 run-scoped 模型鏈覆寫欄位，比照既有 provenance-only 欄位排除於 semantic match 之外。
- 覆寫於 claim（或首次 dispatch）時凍結，resume／retry 沿用凍結值不重新依共享 registry 選擇。
- 三段各自可獨立覆寫，未指定者回退共享 registry。
- 覆寫仍須通過 capability 與 independence domain 檢查，違反即 fail closed 且不靜默退回預設；未知 identity 時列出可用候選。
- durable evidence 記錄三段實際解析結果與來源標記（run-scoped override / shared registry）。

## Capabilities

### Modified Capabilities
- 詳見 `docs/superpowers/specs/per-work-model-chain-spec.md` 的 Requirements 與 `docs/superpowers/specs/per-work-model-chain-design.md` 的 Decisions。
