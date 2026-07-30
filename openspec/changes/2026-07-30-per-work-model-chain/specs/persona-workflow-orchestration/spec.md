## ADDED Requirements

### Requirement: 模型鏈覆寫必須為 run-scoped

`cortex work` 相關動作 MUST 支援 run-scoped 的 planner／builder／reviewer 模型鏈覆寫。覆寫 MUST 只作用於該 run，MUST NOT 改變共享 `model-identities.yaml`，也 MUST NOT 影響其他 active run 尚未派出的 card。

#### Scenario: 覆寫不影響其他 run

- **WHEN** 為某個 WorkItem 指定 builder 模型
- **THEN** 其他 active run 尚未派出的 card 選擇結果不變
- **THEN** 共享 `model-identities.yaml` 未被修改

### Requirement: 覆寫必須於 claim 時凍結

覆寫值 MUST 於 claim（或首次 dispatch）時凍結進 run 記錄。後續 resume／retry-build／retry-verify／retry-review MUST 沿用凍結值，MUST NOT 重新依共享 registry 選擇，除非 operator 明確再次覆寫。三段 MUST 可各自獨立覆寫，未指定者回退共享 registry。

#### Scenario: resume 沿用凍結值

- **WHEN** claim 後共享 registry 順序改變，operator 執行 `resume`
- **THEN** 該 run 沿用 claim 當時凍結的模型鏈

#### Scenario: 部分覆寫

- **WHEN** 只覆寫 builder 而未指定 planner 與 reviewer
- **THEN** planner 與 reviewer 回退共享 registry 選擇

### Requirement: 覆寫不得放寬既有約束

覆寫指定的 identity MUST 通過既有 capability 檢查，且 builder 與 reviewer 的 `independence_domain` MUST NOT 相同。指定不存在或不符約束的 identity 時 MUST fail closed 並回報具體原因，MUST NOT 靜默退回共享 registry 預設選擇。

#### Scenario: 違反 independence domain

- **WHEN** 覆寫使 builder 與 reviewer 落在同一 independence domain
- **THEN** fail closed 並回報原因，不靜默退回預設

#### Scenario: 指定不存在的 identity

- **WHEN** 覆寫指定的 model 不存在於 registry
- **THEN** fail closed，且錯誤訊息列出該 capability 下可用的 identity

### Requirement: 模型鏈解析結果必須可稽核

run 的 durable evidence MUST 記錄三段各自實際解析到的 executor、model 與來源（run-scoped 覆寫或共享 registry）。

#### Scenario: 稽核解析來源

- **WHEN** 事後檢視某 run 的 evidence
- **THEN** 可看出三段各自的 executor 與 model
- **THEN** 可區分該結果來自 run-scoped 覆寫或共享 registry
