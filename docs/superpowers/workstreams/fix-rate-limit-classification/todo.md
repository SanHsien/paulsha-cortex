---
status: accepted
work_item: fix-rate-limit-classification
---

# fix-rate-limit-classification Todo

## Tasks

- [ ] providers.py 分類順序修正（rate limit 判定先於 auth 字樣）
- [ ] `_authority_from_canonical_row` 對 rate-limit degraded 給專屬 reason code
- [ ] doctor gh-auth 區分限流與憑證失效
- [ ] durable backoff deadline，operator resume 不再立即重撞
