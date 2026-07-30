---
status: accepted
work_item: persona-enforce-required-check
---

## Goals

把 persona enforcement 從 shadow 切到 enforce，並將 `persona-scope` 設為 main 的 required status check，讓 persona 契約真正具備約束力。

## Why

目前 `personas.yaml` enforcement 為 shadow、`persona-scope.yml` 恆 exit 0 且非 required check，persona 的 write scope 契約沒有實際約束力；但切換前必須先證明零誤殺，否則 enforce 上線即製造假陽性並促使豁免被濫用。

## What Changes

- 實作可重跑的歷史變更集回放（近期已合併 PR 的檔案清單 → persona scope 判定），證明零誤殺並納入測試。
- `personas.yaml` enforcement 由 shadow 切為 enforce；`persona-scope.yml` 違規時回非零並輸出可定位訊息（persona／路徑／規則）。
- 將 `persona-scope` 設為 main 的 required status check，並將設定步驟記錄於 docs。
- `policy-exempt:persona-scope` 豁免時不阻擋合併，但仍輸出違規內容與理由（不靜音）。

## Capabilities

### Modified Capabilities
- 詳見 `docs/superpowers/specs/persona-enforce-required-check-spec.md` 的 Requirements 與 `docs/superpowers/specs/persona-enforce-required-check-design.md` 的 Decisions。
