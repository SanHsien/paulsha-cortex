---
status: accepted
work_item: terminal-result-contract
---

# terminal-result-contract Specification

#261：讓 terminal/result contract 能誠實表達 gate failure，消除「模型自稱 passed 但 gate 實際失敗」的 fail-open 破口，並把 StructuredOutput schema mismatch 收斂為有上限的確定性失敗。

## 背景

2026-07-30 auto-run dogfood #252～#254 期間出現三個互相放大的問題：

1. build 過程已看到 OpenSpec strict validation failure，模型仍輸出 `status: passed` 的 terminal card；harvest 缺少確定性 cross-check，把「執行內容失敗」與「terminal 自稱成功」混為一談。
2. verifier 路徑的輸出契約沒有完整容納 `failed`／`needs_human` 與結構化 gate diagnostics，模型傾向只能回成功形狀。
3. StructuredOutput wrapper 多次回傳非 canonical 欄位（例如外層包了 `input`／`params`），引發 schema validation retry；相同的確定性格式錯誤被反覆送回模型，消耗大量 token 仍不保證產出 terminal evidence。

這是本 repo 目前唯一的 **fail-open** 風險：其餘 lifecycle 缺陷的後果是卡住（fail-closed，浪費時間），本問題的後果是讓失敗的 candidate 被當成成功放行。

## Goals

- 成功必須由 gate evidence 證明，模型文字與 exit code 不能自行授權成功。
- 失敗必須可以被誠實表示，三種終局狀態（passed／failed／needs_human）在契約上對等可達。
- 確定性的格式錯誤只處理有限次，不得形成無上限的 retry storm。

## Requirements

### R1 canonical result envelope

SHALL 定義單一版本化的 terminal/result envelope，供 build、verify、review 三類 card 共用。envelope MUST 含明確的版本欄位，並且 MUST 完整支援 `passed`、`failed`、`needs_human` 三種終局狀態（或等價的完整狀態集合）。

各 card kind MUST 能在該 envelope 內合法表達成功、失敗、需人工介入與結構化 diagnostics；不得存在「只有成功形狀是合法的」路徑。

### R2 passed 必須有 gate evidence 背書

宣告 `passed` 的 terminal MUST 引用 manager 可重新驗證的 gate evidence。harvest MUST 在採信 `passed` 之前重跑或重讀該 evidence。

當 gate command 已經失敗時，harvest MUST NOT 接受與其矛盾的 `passed`；此時 MUST fail closed，並保留矛盾的具體原因（哪一個 gate、期望值與實際值）供 operator 判讀。

模型輸出的自然語言、exit code 為 0、以及「沒有明確錯誤」三者皆 MUST NOT 單獨構成成功授權。

### R3 schema mismatch 為有上限的確定性失敗

StructuredOutput 的 schema mismatch MUST 保留 machine-readable 的 validation errors。

normalization MUST 僅針對明確白名單形狀（例如已知的 wrapper 外層鍵），且同一個確定性 mismatch MUST 只嘗試修復一次；不得以寬鬆解析吞掉未知欄位，也不得對同一形狀無限重試模型。

retry MUST 有明確上限與計數器，且該計數 MUST 可從 status／inspect 介面觀察（含 validation path 與 reason）。

### R4 診斷不因 parse 失敗而遺失

terminal parse 失敗時，MUST NOT 遺失 candidate／worktree 的唯讀診斷資訊（observed HEAD、job id、失敗原因）。

同時 MUST NOT 因為保留了這些診斷資訊就授予 candidate authority——可觀測與可授權是兩件事。

## 非目標

- 不在本次變更調整 retry 的分類語意（#215／#216 已定案的 `RetryClassification` enum 不改名、不擴充）。
- 不處理 repair commit 的 evidence adoption（屬 #260 範圍）。
- 不調整 lifecycle 的 stage ordering（屬 #263 範圍）。

## 驗收面

- 任一確定性 gate（OpenSpec／pytest／policy）失敗而 terminal 自稱 `passed` 時，manager fail closed 並保留矛盾原因。
- build／verify／review 三類 card 各自可合法輸出 success、failure、needs-human 與 diagnostics。
- 常見錯誤 wrapper 形狀：可安全 normalize 者只處理一次，不可處理者終止為可操作錯誤。
- schema retry 有上限與計數器，且 status surface 顯示 validation path 與 reason。
- terminal parse 失敗時診斷資訊仍在，且未授予 authority。
