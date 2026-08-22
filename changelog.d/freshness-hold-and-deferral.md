### Added
- 依賴新鮮度檢查新增兩條「已評估但不該升」的正當出口：宣告行上的 `# freshness-hold: <理由>`（長期政策），以及 `.github/dependency-deferrals.json` 的 `deferredLatest` + `reason`（這次不升，PyPI 超過該版本即自動失效）。沒有 `deferredLatest` 的條目直接忽略——那等於永久靜音，不是延後。報告顯示「維持宣告／已延後」，彙總只算真正未處理的。
