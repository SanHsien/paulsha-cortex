## ADDED Requirements

### Requirement: Doctor runtime validator failure 必須安全且可執行

`cortex doctor` 與 `cortex inspect doctor --json` MUST 在 required runtime contract 驗證失敗時保留穩定 reason category 與修復下一步；MUST NOT 回顯 exception payload、secret marker、完整命令內容或不必要的個人絕對路徑。Probe 名稱、requiredness、fail-closed exit 語意與 `cortex-doctor/v1` schema MUST 維持相容。

#### Scenario: Preflight command 未設定

- **WHEN** `PSC_PREFLIGHT_CMD` 缺失或為空
- **THEN** preflight probe 以 required category FAIL，訊息指出必須設定 `PSC_PREFLIGHT_CMD`
- **THEN** doctor 整體維持 non-ready 與非零 exit

#### Scenario: Preflight command 格式或 executable 無效

- **WHEN** runtime validator 回報 malformed、禁止 shell wrapper 或 executable-unavailable
- **THEN** preflight probe 分別輸出可區辨的安全 category 與對應修復下一步
- **THEN** detail 不包含 validator exception 中的任意絕對路徑或 secret marker

#### Scenario: Model identity registry 無效

- **WHEN** runtime validator 回報 identity registry missing、unreadable 或 schema/contract-invalid
- **THEN** model-identities probe 保留可區辨的安全 category 與修復方向
- **THEN** detail 不回顯 registry 內容、個人絕對路徑或 secret marker

#### Scenario: Valid runtime contract

- **WHEN** preflight command 與 model identity registry 都通過既有 runtime validator
- **THEN**兩個 probe 維持既有 PASS 狀態與相容 detail
