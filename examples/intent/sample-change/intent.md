---
schema: cortex-intent/v1
work_item: sample-change
status: draft
owner: product-owner
---

# Sample change intent

## Problem

使用者無法從現有狀態判斷某項工作為何被提出，以及哪些限制不得被實作繞過。

## Proposed outcome

在進入 spec 與 plan 前，建立一份短而可版本控制、經人類修正的意圖紀錄。

## Affected users and systems

- 提出需求及核准範圍的產品負責人。
- 後續建立 spec、plan 與驗收條件的工程人員或 agent。

## Constraints

- intent 不得直接觸發 claim、start 或 dispatch。
- 核准證據必須綁定 exact Git commit SHA。

## Out of scope

- 不在 intent 階段決定完整技術設計。
- 不自動啟動任何 executor。

## Evidence and sources

- 原始 ticket、incident 或研究來源應以可重讀 reference 列在這裡。

## Open questions

- 這個變更的 acceptance criteria 應由哪份後續 spec 擁有？

## Success signals

- 後續 spec 與 plan 能回指本檔的 repo-relative path 和 exact SHA。
- 未核准或已修改的 intent 不會取得派工 authority。
