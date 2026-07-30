## MODIFIED Requirements

### Requirement: terminal result 必須以版本化 envelope 誠實表達三種終局狀態

terminal/result contract MUST 使用帶 `schema_version` 的 canonical envelope，且 MUST 完整支援 `passed`、`failed`、`needs_human` 三種終局狀態與結構化 diagnostics。build、verify、review 三類 card MUST 共用同一 envelope，MUST NOT 存在只有成功形狀合法的路徑。

#### Scenario: 三種終局狀態皆可表達

- **WHEN** build、verify 或 review card 需要回報成功、失敗或需人工介入
- **THEN** 各狀態皆可於 canonical envelope 內合法表達並帶結構化 diagnostics
- **THEN** envelope 帶明確 `schema_version`

#### Scenario: 舊形狀相容

- **WHEN** harvest 讀到不帶 `schema_version` 的既有 payload
- **THEN** 走相容讀取路徑並記可觀測的 legacy 標記
- **THEN** 不因版本差異而拒收既有 run

### Requirement: passed 必須由可重驗的 gate evidence 授權

宣告 `passed` 的 terminal MUST 引用 manager 可重新驗證的 gate evidence，harvest MUST 於採信前重讀並驗證。模型輸出的自然語言、exit code 為 0、以及無明確錯誤，三者皆 MUST NOT 單獨構成成功授權。gate command 已失敗時 harvest MUST NOT 接受矛盾的 `passed`。

#### Scenario: 缺 gate evidence 的 passed

- **WHEN** terminal 宣稱 `passed` 但無可重驗的 gate evidence
- **THEN** manager fail closed 並保留缺少 evidence 的原因

#### Scenario: 與失敗 gate 矛盾的 passed

- **WHEN** 確定性 gate（OpenSpec／pytest／policy）已失敗而 terminal 自稱 `passed`
- **THEN** manager fail closed
- **THEN** 保留矛盾的具體原因，含 gate 名稱、期望值與實際值

### Requirement: schema mismatch 必須是有上限的確定性失敗

StructuredOutput 的 schema mismatch MUST 保留 machine-readable validation errors。normalization MUST 僅針對明確白名單形狀且同一確定性 mismatch MUST 只嘗試一次。retry MUST 有明確上限與計數器，且該計數 MUST 可從 status／inspect 觀察。

#### Scenario: 已知 wrapper 形狀

- **WHEN** StructuredOutput 回傳已列於白名單的外層包裝鍵
- **THEN** normalize 一次即成功，且不回派模型

#### Scenario: 未知 wrapper 形狀

- **WHEN** StructuredOutput 回傳白名單以外的形狀
- **THEN** 終止為可操作錯誤，不以寬鬆解析吞掉未知欄位
- **THEN** retry 計數不超過上限，且 status 顯示 validation path 與 reason

### Requirement: parse 失敗不得遺失診斷也不得授予 authority

terminal parse 失敗時 MUST NOT 遺失 candidate／worktree 的唯讀診斷資訊（observed HEAD、job id、失敗原因），同時 MUST NOT 因保留該資訊而授予 candidate authority。

#### Scenario: terminal 無法解析

- **WHEN** terminal payload 無法解析為 canonical envelope
- **THEN** observed HEAD、job id 與失敗原因仍可於 status 觀察
- **THEN** 該 candidate 未取得 authority，後續動作仍需明確授權
