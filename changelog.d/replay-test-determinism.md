### Fixed
- **Issue #284：persona 歷史回放測試改釘固定錨點**：`test_historical_replay_has_zero_false_positives`
  原以浮動的 `main` ref 回放，merge／rebase 進行中 `prs_scanned` 可能落到 0 而讓斷言失敗
  （「掃不到」被誤判為「有誤殺」）；且 `actions/checkout` 預設 shallow，CI 實際回放範圍
  遠少於宣稱的 30 個 PR 卻仍通過。改釘固定 commit 錨點使結果不隨 HEAD 移動而改變，
  並在錨點不可解析（淺 clone）時明確 skip 而非靜默通過。`replay.py` CLI 的動態回放不受影響。
