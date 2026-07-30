---
status: accepted
work_item: persona-enforce-required-check
---

# persona-enforce-required-check Specification

#135：把 persona enforcement 從 shadow 切到 enforce，並將 `persona-scope` 設為 main 的 required status check，讓 persona 契約真正具備約束力。

## 背景

目前 `personas.yaml` 的 enforcement 為 `shadow`，`persona-scope.yml` 恆 `exit 0` 且非 required check——只觀察、不阻擋。也就是說 persona 的 write scope 契約現在沒有實際約束力：違反 scope 的變更可以正常合併。

來源為 umbrella 設計 §3 / §5 與 #112。

切換的前提是契約本身已調到零誤殺；在誤殺存在的情況下開啟 enforce，會讓合法變更被無故擋下，反而促使 operator 濫用豁免 label，使規則失去意義。

## Goals

- persona write scope 契約具備實際約束力，違反時能阻擋合併。
- 切換前先證明零誤殺，避免 enforce 上線即製造大量假陽性。
- 保留明確且有紀錄的豁免途徑，供合法例外使用。

## Requirements

### R1 切換前證明零誤殺

SHALL 在切到 enforce 之前，以既有歷史變更集（近期已合併的 PR 檔案清單）回放 persona scope 判定，並證明零誤殺。

若存在誤殺，MUST 先修正契約或 scope 定義，MUST NOT 以放寬檢查或加大豁免範圍的方式達成零誤殺。

### R2 enforcement 切換

`personas.yaml` 的 enforcement SHALL 由 `shadow` 切為 `enforce`。

`persona-scope.yml` SHALL 在偵測到違規時回傳非零，並輸出足以定位的訊息（哪個 persona、哪些路徑、違反哪條 scope 規則）。

### R3 required status check

`persona-scope` SHALL 設為 main 的 required status check。

### R4 豁免機制

SHALL 提供 `policy-exempt:persona-scope` 豁免 label；套用時 MUST 記錄理由，且 MUST NOT 因豁免而略過訊息輸出（仍需顯示被豁免的違規內容，供事後稽核）。

## 非目標

- 不重新定義各 persona 的 write scope 內容（本次只切換 enforcement 模式）。
- 不改其他 policy 規則的 gate 行為。

## 驗收面

- 以歷史變更集回放，persona scope 判定零誤殺，且該回放可重跑。
- `personas.yaml` enforcement 為 `enforce`。
- 違規時 `persona-scope.yml` 回非零並輸出可定位訊息。
- `persona-scope` 為 main 的 required status check。
- `policy-exempt:persona-scope` 可豁免，且豁免時仍輸出違規內容與理由。
