---
status: accepted
work_item: dedupe-legacy-config-warnings-delivery
---

## Context

`_resolve_config_source()` 依序處理 explicit path、`PSC_MONITOR_CONFIG`、
`PAULSHACLAW_CONFIG`、新 manual file 與 legacy manual file。後兩個 legacy
來源直接在 resolution path 呼叫 `warnings.warn(..., stacklevel=2)`；長駐 process
反覆掃描時 caller location 與 warning filter 無法提供可靠的 process-level 去重。

## Goals / Non-Goals

**Goals:**

- legacy env 與 legacy file fallback 的 warning 各自每 process 最多一次。
- 首次 warning message 與 stacklevel 保持不變。
- config precedence、resolved path 與不存在時回傳 `None` 的行為不變。
- regression 在 `simplefilter("always")` 下仍能證明 once contract。

**Non-Goals:**

- 不移除 legacy config 支援或自動搬移檔案。
- 不改 warning category、文案或導入 logging subsystem。
- 不跨 process 去重；每個 CLI process 仍可提醒一次。

## Decisions

### 1. 使用 module-local stable key set

新增私有 set 與 helper `_warn_deprecated_once(key, message)`。每條 legacy path
使用固定 key；helper 僅在 key 未出現時呼叫 `warnings.warn()`，成功後才記錄。
這讓行為不受 stacklevel/caller location 或外部 `simplefilter("always")` 影響。

### 2. 兩條 warning 各自保留一次

legacy env 與 legacy file fallback 提供不同遷移資訊，因此不是全 module 共用一個
boolean。每條路徑各自一次，兼顧降噪與遷移可見性。

### 3. 測試直接隔離 module state

Regression 以 monkeypatch 或 fixture 清空私有 set，避免測試執行順序污染；不新增
production reset API。測試逐字比對首次訊息，並驗證重複 resolve 的 path 不變。

## Risks / Trade-offs

- [Risk] module state 讓同 process 後續 config 改變時不再重複提醒同一路徑。→
  這正是 issue 要求的 process-level once contract；另一條 legacy path 仍有獨立 key。
- [Risk] warning filter 設為 error 時 `warnings.warn()` 會拋出。→ 只有成功返回後才
  記錄 key，保留既有 warning-as-error 行為。

## Migration Plan

無資料遷移。升級後每個新 process 第一次使用各 legacy source 時照常提醒，後續
掃描不再重複；改用新 config 後完全不警告。

## Open Questions

無。
