# 上游追蹤改以 release 為單位

- `tools/check_upstream_updates.py` 新增 `track` 模式（`release` 預設／`commit`）。release 模式讀上游的
  semver tag，只有出現「還沒審過的 release」才失敗，並列出該 release 相對 baseline 的 commit；tag 解析取
  annotated tag 的 peeled commit，排序用版本數值而非字串（`v0.1.10` 要排在 `v0.1.7` 之後）。
- `tools/upstream_baseline.json` 設為 `track: "release"`、`reviewed_release: "v0.1.8"`。理由：本 fork 四次
  同步全部錨定上游 tag，而上游 `main` 每天多次變動；追 `main` 會讓每週檢查永遠紅燈，而永遠紅燈的檢查沒有人會讀。
- `docs/UPSTREAM.md` 記錄 2026-08-22 的批次檢視：`dc8a968`（v0.1.8）之後累積 202 個 commit、50 個 merged PR、
  420 個檔案、+124k 行，上游尚未發版，決定等下一個 tag 再整批評估。
- 依賴宣告下限對齊 CI 實際解析的版本：`pytest>=9.1`、`build>=1.5`、`twine>=7`、`setuptools>=84`（`PyYAML>=6`
  不變）。這些不是漏升級，是宣告落後於 CI 早就在用的版本。
- `tests/test_maintenance_checks.py` 補 5 條：tag 解析與版本排序、空 tag 清單、baseline 必須宣告 release 模式、
  未知 track 模式要拒絕、release 模式的乾淨與命中兩種報告文字。
