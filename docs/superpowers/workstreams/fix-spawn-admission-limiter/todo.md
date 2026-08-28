---
status: accepted
work_item: fix-spawn-admission-limiter
---

# fix-spawn-admission-limiter Todo

## Tasks

- [ ] fanout lane（dispatch_ready）加 per-provider spawn admission limiter
- [ ] workflow lane periodic tick 同樣受限
- [ ] 預算按每次 spawn 的 credential-probe 次數估（三來源各帶重試）
- [ ] regression test 驗 spawn timestamp 間隔而非全序列化
