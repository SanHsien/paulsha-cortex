---
status: accepted
work_item: fix-doctor-diagnostics-delivery
domain_breadth: 0
state_consistency: 0
---

## 1. RED regression

- [x] 1.1 在 `tests/test_doctor.py` 新增 preflight required、malformed、shell-wrapper、executable-unavailable 的 probe detail 測試，並先確認 focused suite 因現行泛化訊息失敗。
- [x] 1.2 新增 identity missing、unreadable、schema/contract-invalid 與 secret／absolute-path 不洩漏測試，並先確認 RED 原因正確。

## 2. Actionable diagnostics

- [x] 2.1 在 `paulsha_cortex/doctor.py` 實作 allowlisted preflight reason 分類與固定下一步，維持既有 probe schema、requiredness 與 fail-closed exit。
- [x] 2.2 在 `paulsha_cortex/doctor.py` 實作 allowlisted model-identity reason 分類；未知 exception 使用不含 payload 的安全 fallback。
- [x] 2.3 跑 `tests/test_doctor.py` 與相關 inspect/CLI regression，確認所有新增分類、成功路徑與敏感資訊邊界通過。

## 3. Documentation and governance

- [x] 3.1 更新 `README.md`，加入 `PSC_PREFLIGHT_CMD` 用途、typed argv 格式及 shareable-safe placeholder 範例。
- [x] 3.2 更新 `docs/onboarding/quickstart.md`，在第一次 doctor 前交代必要設定；更新 `docs/onboarding/troubleshooting.md`，涵蓋 required、malformed、shell-wrapper、executable-unavailable 排除方式。
- [x] 3.3 更新 `CHANGELOG.md` `[Unreleased]`，加入含 `#252` 的 Fixed 條目。
- [x] 3.4 跑 `python3 -m pytest` 全套、`openspec validate --all`、`python3 -m policy_check --repo .` 與 `git diff --check`。
- [x] 3.5 將本 tasks 全部勾選，保留一票一個 conventional commit，供 Cortex ForeignReview 與 delivery gate 驗證。
