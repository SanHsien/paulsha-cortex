# 依賴與上游的排程檢查

- 新增 `tools/check_dependency_freshness.py` 與 `.github/workflows/dependency-freshness.yml`：
  每月 1 日盤點 `pyproject.toml` 的 runtime、extras 與 build backend 宣告，對 PyPI 現行版本
  比對，並把 open Dependabot PR 併進同一份報告。版本比較採「宣告精度」——`>=6` 只比 major，
  所以 `PyYAML>=6` 對 6.0.3 不會變成每月的假警報。
- 新增 `tools/check_upstream_updates.py`、`tools/upstream_baseline.json` 與
  `.github/workflows/upstream-check.yml`：每週一比對 `hamanpaul/paulsha-cortex` 的 main 與
  baseline 的 `reviewed_through`，列出未審 commit 與其變動檔案。baseline 從
  `dc8a968`（v0.1.8，2026-08-12 已審）起算，首次執行即顯示上游此後累積的 199 個 commit。
- 新增 `tests/test_maintenance_checks.py`：兩支檢查器的離線契約測試，包含 baseline 的
  `reviewed_through` 與 `reviewed_date` 必須在 `docs/UPSTREAM.md` 找得到。
- 兩支檢查器都只讀不寫：不看已安裝環境、不改宣告、不推進 baseline。
