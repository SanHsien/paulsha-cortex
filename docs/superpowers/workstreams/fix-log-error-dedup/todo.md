---
status: accepted
work_item: fix-log-error-dedup
---

# fix-log-error-dedup Todo

## Tasks

- [ ] `_log_error` 單槽去重改多槽（LRU/TTL 有界）
- [ ] 新增交錯多 signature 的回歸測試（3+ signature 輪替下抑制摘要仍生效）
- [ ] 保留既有單 signature 行為與 `LOG_ERROR_SUMMARY_INTERVAL` 週期摘要

> 2026-08-10：首次 claim（workflow-6569c45012d9c2b84db9）因 define 靜默失敗 abandon；本行推進 authority digest 以重新 claim。
