---
status: accepted
work_item: planning-claim-recovery
---

# planning-claim-recovery Specification

#256：讓「在壞環境下 claim 過一次」的 work item 可以在環境修好後前向恢復，消除目前四個恢復桿全部無效、唯一出口 `abandon` 會卡成另一種永久死的狀態。

## 背景

work-item workflow run 一旦在 planning identity 不可用的環境下被 claim，就永久停在 `define` / `needs_human`，且沒有任何前向復原路徑——planning runtime 只在 claim 當下執行一次，事後把環境修好也救不回來。

本機歷史紀錄顯示這不是偶發：三個 run、兩個 work item、跨兩天，全部停在 `define`，builder job 一個都沒派出過。

四個恢復桿逐一實測皆無效：`cortex work resume` 對 `active_status == "needs_human"` 直接原樣回報、不重跑 planning；新增 planning 產物只對慣例路徑有效；`cortex work link` 只重排 `.cortex/work-items.yaml` 區塊而 digest 不變；`cortex tick` 只驅動 deck/spec fanout、不推進 work-item run。剩下唯一的 `abandon` 會讓 work item 留在 `blocked`，且 `start` / `resume` 全部短路在 `persisted-block`。

觸發器（planning identity probe 失敗）已由 #255 修復，但本 issue 的核心缺陷——**一次性 planning 執行 + 無前向恢復**——仍然存在，且現在可以在乾淨環境下驗證。

## Goals

- 環境修復後，卡在 `define` 的 run 有明確、有界、可稽核的前向恢復路徑。
- `abandon` 不再是「換一種永久死」，而是能真正釋放 work item 讓它重新被 claim。
- 恢復動作維持 fail-closed：不得為了讓 run 前進而放寬 authority 或 planning 完整性要求。

## Requirements

### R1 planning 可在環境修復後重跑

SHALL 提供明確的恢復動作，使停在 `define` / `needs_human` 且失敗原因為環境面（planning identity 不可用、probe 失敗、runtime 缺失）的 run，能在環境修復後重新執行 planning，而不需要重新 claim。

該動作 MUST 驗證失敗原因確實屬於可恢復類別；內容面的 planning 失敗（產物缺失、blocking marker 未解）MUST NOT 由本路徑繞過。

### R2 resume 對 needs_human 給出可執行下一步

`cortex work resume` 遇到 `active_status == "needs_human"` 時 MUST NOT 只原樣回報狀態。回應 MUST 帶出 blocking reason 與該狀態下合法的動作集合，讓 operator 或 agent 不需翻 registry 就知道下一步。

### R3 abandon 真正釋放 work item

`abandon` 之後，同一 work item MUST 能以修復後的環境重新 claim，不得因 `persisted-block` 而使 `start` / `resume` 全部短路。

若既有的 claim key 唯一性設計（repo + work_id + authority digest）與此衝突，MUST 提供明確的釋放語意，使 abandon 後的重新 claim 是受支持的正常流程，而非只能靠變更 authority 組成（例如新增檔案改變 digest）來繞過。

### R4 恢復動作可稽核且冪等

每次恢復動作 MUST 記錄觸發者、判定為可恢復的依據、以及恢復前後的 run 狀態。

同一恢復請求重送 MUST NOT 產生第二個 planning job 或第二個 run。

## 非目標

- 不改 planning identity 的 probe 比對邏輯（#255 已修）。
- 不改 planning artifacts 的完整性判定（`assess_planning_completeness` 契約不動）。
- 不處理 build 之後的 candidate 恢復（屬 #260 範圍）。

## 驗收面

- 在 planning identity 不可用時 claim 的 run，環境修復後可經明確動作重跑 planning 並離開 `define`。
- 內容面的 planning 失敗不因本路徑被繞過。
- `resume` 對 `needs_human` 回傳 blocking reason 與合法動作集合。
- `abandon` 後同一 work item 可重新 claim，不需變更 authority 組成。
- 恢復動作有稽核紀錄，且重送具冪等性。
