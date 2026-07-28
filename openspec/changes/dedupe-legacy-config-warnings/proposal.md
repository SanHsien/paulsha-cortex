---
status: accepted
work_item: dedupe-legacy-config-warnings-delivery
---

## Why

長駐 manager process 每次 monitor config resolution 選到 legacy
`PAULSHACLAW_CONFIG` 或 legacy `paulshaclaw.yaml` fallback 時都輸出相同
deprecation warning。警告不會自行停止，會持續污染 daemon log 並淹沒真正的
runtime 訊號。

## Goals

- 兩條 legacy config 遷移警告在同一 process 內各自最多輸出一次。
- 保留首次完整警告文字、resolved path 與 config precedence。
- 新 config env/file 路徑維持零 legacy warning。

## What Changes

- 在 monitor config module 建立穩定 deprecation key 與 per-process warning
  deduplication helper。
- legacy env 與 legacy file fallback 使用不同 key，但共享相同 once contract。
- 新增強制 warning filter 的 regression，證明去重不依賴 caller location。

## Capabilities

### New Capabilities

- `monitor-config-resolution`: monitor config source selection 必須保持 precedence，
  並限制 legacy migration warning 為每 process 每路徑一次。

### Modified Capabilities

無。

## Impact

- 修改 `paulsha_cortex/monitor/config.py` 與直接相關 config resolution tests。
- 更新 changelog 與必要 config migration 文件。
- 不新增依賴、不改 warning message、不改 config path precedence。
