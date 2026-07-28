---
status: accepted
work_item: fix-doctor-diagnostics
---

# Tasks

- [x] Task 1 Step 1: 加入 preflight reason RED 測試（required / malformed / shell-wrapper / executable unavailable）
- [x] Task 1 Step 2: 加入 identity reason 與敏感資訊邊界 RED 測試（missing / unreadable / schema-invalid / unknown error）
- [x] Task 1 Step 3: 執行 RED regression（`pytest tests/test_doctor.py -q`）
- [x] Task 1 Step 4: 提交 RED test
