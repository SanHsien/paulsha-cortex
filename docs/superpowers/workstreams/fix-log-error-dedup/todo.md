---
status: accepted
work_item: fix-log-error-dedup
---

# fix-log-error-dedup Todo

## Tasks

- [ ] `_log_error` 單槽去重改多槽（LRU/TTL 有界）
- [ ] 新增交錯多 signature 的回歸測試（3+ signature 輪替下抑制摘要仍生效）
- [ ] 保留既有單 signature 行為與 `LOG_ERROR_SUMMARY_INTERVAL` 週期摘要
