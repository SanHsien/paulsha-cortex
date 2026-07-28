## MODIFIED Requirements

### Requirement: 新手必須能依 Quickstart 文件獨立完成第一個 workflow

`docs/onboarding/quickstart.md` MUST 涵蓋 pipx install → 必要 `PSC_PREFLIGHT_CMD` 設定 → `cortex bootstrap` → doctor 驗證 → 第一個 workflow 的完整步驟，且 MUST NOT 要求讀者具備 deck/spec 內部概念的先備知識。README MUST 說明該環境變數的用途、typed argv 格式與 shareable-safe 範例；`docs/onboarding/troubleshooting.md` MUST 提供 required、malformed 與 executable-unavailable FAIL 的排除步驟。

#### Scenario: 新手依 Quickstart 操作

- **WHEN** 一位未使用過 cortex 的使用者依序執行 Quickstart 文件列出的命令
- **THEN** 使用者在第一次 doctor 前已知道如何設定專案提供的 `PSC_PREFLIGHT_CMD`
- **THEN** 使用者可在文件描述的步驟內完成第一個可觀察的 workflow 結果
- **THEN** 過程中不需要另外查閱 Concepts 文件即可完成操作或排除 preflight probe FAIL
