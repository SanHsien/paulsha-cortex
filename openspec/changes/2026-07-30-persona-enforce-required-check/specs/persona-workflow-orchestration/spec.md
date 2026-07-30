## MODIFIED Requirements

### Requirement: persona enforcement 切換前必須證明零誤殺

切至 `enforce` 之前 MUST 以既有歷史變更集回放 persona scope 判定並證明零誤殺，該回放 MUST 可重跑。若存在誤殺 MUST 先修正契約或 scope 定義，MUST NOT 以放寬檢查或加大豁免範圍達成零誤殺。

#### Scenario: 歷史回放零誤殺

- **WHEN** 以近期已合併 PR 的檔案清單回放 persona scope 判定
- **THEN** 判定結果零誤殺
- **THEN** 該回放可重跑，供日後修改 scope 定義時檢查影響

#### Scenario: 發現誤殺

- **WHEN** 回放顯示合法變更被判為違規
- **THEN** 修正契約或 scope 定義本身
- **THEN** 不以放寬檢查或擴大豁免使回放通過

### Requirement: persona-scope 必須具備阻擋能力並可定位

`personas.yaml` 的 enforcement MUST 為 `enforce`；`persona-scope.yml` 偵測到違規時 MUST 回非零，且輸出 MUST 含 persona、實際觸及路徑與違反的 scope 規則。`persona-scope` MUST 為 main 的 required status check。

#### Scenario: 違規被擋下

- **WHEN** PR 的變更超出該 persona 的 write scope
- **THEN** `persona-scope` 回非零並阻擋合併
- **THEN** 輸出含 persona、觸及路徑與違反的規則

### Requirement: 豁免不得靜音

套用 `policy-exempt:persona-scope` 時 MUST NOT 阻擋合併，但 MUST 仍輸出違規內容並記錄理由，供事後稽核。

#### Scenario: 套用豁免

- **WHEN** PR 帶 `policy-exempt:persona-scope` label 且存在 scope 違規
- **THEN** 不阻擋合併
- **THEN** 仍輸出違規內容與理由，可供事後稽核使用頻率
