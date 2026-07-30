---
status: accepted
work_item: terminal-result-contract
---

## Goals

讓 terminal/result contract 能誠實表達 gate failure，消除「模型自稱 passed 但 gate 實際失敗」的 fail-open 破口，並把 StructuredOutput schema mismatch 收斂為有上限的確定性失敗。

## Why

這是本 repo 目前唯一的 fail-open 風險：其餘 lifecycle 缺陷的後果是卡住（fail-closed，浪費時間），本問題的後果是讓失敗的 candidate 被當成功放行，同時 schema mismatch 的無上限重試造成大量 token 消耗。

## What Changes

- 定義帶 `schema_version` 的 canonical result envelope，完整支援 `passed`／`failed`／`needs_human` 三種終局狀態與結構化 diagnostics；舊形狀走相容路徑並記 legacy 標記。
- harvest 在採信 `passed` 前重讀並驗證 gate evidence；確定性 cross-check 排在狀態採信之前，偵測到矛盾即 fail closed 並保留具體原因。
- StructuredOutput normalization 採白名單且同一確定性 mismatch 只嘗試一次；retry 有上限與計數器，未知形狀終止為可操作錯誤而非回派模型。
- parse 失敗時保留 observed HEAD／job id／reason 的唯讀診斷，與 authority 欄位分離。
- status／inspect 顯示 schema retry 計數、validation path 與 reason。

## Capabilities

### Modified Capabilities
- 詳見 `docs/superpowers/specs/terminal-result-contract-spec.md` 的 Requirements 與 `docs/superpowers/specs/terminal-result-contract-design.md` 的 Decisions。
