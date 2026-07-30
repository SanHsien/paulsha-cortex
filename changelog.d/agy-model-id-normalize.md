### Fixed
- **Issue #255：AGY_MODEL_ID 改用 agy 實際輸出的 kebab id**：`AGY_MODEL_ID` 由顯示名
  `Gemini 3.1 Pro (High)` 改為 `gemini-3.1-pro-high`，並為 `probe_agy_capability` 加入
  顯示名↔kebab id 的正規化容錯比對，修正套件預設下唯一 planning identity 永遠 probe
  失敗、work-item workflow 卡死在 `define/needs_human` 的問題；`model-not-listed` 失敗
  改帶出實際可用清單，v1 schema 沿用舊顯示名的設定維持向後相容。
