---
status: accepted
work_item: fix-doctor-diagnostics
---

# Tasks

- [x] Task 1 Step 1: 加入 preflight reason RED 測試（required / malformed / shell-wrapper / executable unavailable）
- [x] Task 1 Step 2: 加入 identity reason 與敏感資訊邊界 RED 測試（missing / unreadable / schema-invalid / unknown error）
- [x] Task 1 Step 3: 執行 RED regression（`pytest tests/test_doctor.py -q`）
- [x] Task 1 Step 4: 提交 RED test
- [x] Task 2 Step 1: 實作 preflight allowlist classifier（required / malformed / shell-wrapper / executable-unavailable）
- [x] Task 2 Step 2: 實作 identity allowlist classifier（missing / unreadable / schema-invalid / canonical planning missing）
- [x] Task 2 Step 3: 接入 probes 並保持成功路徑
- [x] Task 2 Step 4: 跑 focused regression（`pytest tests/test_doctor.py tests/test_porcelain_inspect.py tests/test_cli_help_alignment.py -q`）
- [x] Task 2 Step 5: 提交 implementation
- [x] Task 3 Step 1: 更新 README 的 `PSC_PREFLIGHT_CMD` 合約
- [x] Task 3 Step 2: 更新 quickstart 的 preflight 設定與驗證說明
- [x] Task 3 Step 3: 更新 troubleshooting 的四類 preflight failure
- [x] Task 3 Step 4: 更新 changelog 與 OpenSpec tasks
- [x] Task 3 Step 5: 跑完整驗證（`openspec validate --all`、`python3 -m policy_check --repo .`）
- [x] Task 3 Step 6: 提交 docs/governance
