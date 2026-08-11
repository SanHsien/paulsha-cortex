### Added
- 同步 upstream v0.1.5 到 `b79c74a`，保留原生 Windows runtime；`cg` 經 typed-argv wrapper 傳 stdin，ship-phase cards 啟用 `provider:executor` auth gate。

### Changed
- `docs/UPSTREAM.md` 記錄 41 張 merged PR、Issue #442 的採用／延後決策與下次 review watermark，避免重複處理。
- Windows launcher 在載入跨平台 wrapper 時保留 operator 原有的 `PYTHONPATH`；review-only 環境仍只暴露 repo package root。

### Fixed
- 修正 upstream 合併後的 Windows-only 回歸：POSIX service 測試分流、planning fixture newline authority、Windows mode 語意、hermetic home 隔離、PowerShell PID probe decoding，以及 digest delivery command 的反斜線 argv 解析。
- `cg` prompt 改走真正的 OS stdin pipe，不再進入 wrapper command line，避開 Windows `CreateProcess` 長度上限與 prompt 洩漏。
