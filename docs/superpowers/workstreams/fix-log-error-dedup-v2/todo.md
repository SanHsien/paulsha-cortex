---
status: accepted
work_item: fix-log-error-dedup-v2
---

# fix-log-error-dedup-v2 Todo

## Tasks

- [ ] `_log_error` 單槽去重改多槽（LRU/TTL 有界）
- [ ] 新增交錯多 signature 的回歸測試（3+ signature 輪替下抑制摘要仍生效）
- [ ] 保留既有單 signature 行為與 `LOG_ERROR_SUMMARY_INTERVAL` 週期摘要

> 2026-08-10：v1 識別的三個世代（6569c45012d9／71f912efc167／244b7cfdee54）全數燒於基礎設施缺陷
> （#390 combo 凍結、#397 pycache 誤殺、#399 runtime churn 誤殺、#401 extractor envelope fallthrough），
> 非工作本身失敗；依 #218 世代熔斷的重識別逃生門改為 -v2。
