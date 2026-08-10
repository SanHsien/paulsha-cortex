---
status: accepted
work_item: fix-registry-atomic-transitions
---

# fix-registry-atomic-transitions Todo

## Tasks

- [ ] `record_action`/`update_slice` 改先全驗證再全突變（消除髒寫外洩）
- [ ] gate_state failed 補合法離開路徑並與 slice state 轉換表對齊
- [ ] `allowed_slice_actions` 同時檢視 gate_state
- [ ] 回歸測試覆蓋半突變外洩與 failed/failed 死角復原
