## MODIFIED Requirements

### Requirement: 環境面 planning 失敗必須可前向恢復

停在 `define`／`needs_human` 且失敗原因屬環境面（planning identity 不可用、probe 失敗、runtime 缺失）的 run，MUST 能在環境修復後經明確動作重新執行 planning，且不需重新 claim。內容面失敗（產物缺失、blocking marker 未解）MUST NOT 由本路徑繞過。

#### Scenario: 環境修復後恢復

- **WHEN** planning 曾因 identity 不可用而失敗，且環境已修復
- **THEN** 恢復動作放行並重跑 planning，run identity 與 authority 凍結不變
- **THEN** run 可離開 `define`

#### Scenario: 內容面失敗不被繞過

- **WHEN** planning 因產物缺失或 blocking marker 而失敗
- **THEN** 恢復動作拒絕並回報實際原因

### Requirement: resume 對 needs_human 必須給出可執行下一步

`resume` 遇 `active_status == "needs_human"` 時 MUST NOT 只原樣回報狀態，回應 MUST 帶 blocking reason 與該狀態下合法的動作集合。

#### Scenario: resume 回報阻塞原因

- **WHEN** operator 對停在 `needs_human` 的 run 執行 `resume`
- **THEN** 回應含 blocking reason 與合法動作集合
- **THEN** operator 不需翻 registry 即可決定下一步

### Requirement: abandon 必須真正釋放 work item

`abandon` 之後同一 work item MUST 能以修復後的環境重新 claim，MUST NOT 因 `persisted-block` 使 `start`／`resume` 全部短路。釋放語意 MUST 為受支持的正常流程，而非只能靠變更 authority 組成繞過。

#### Scenario: abandon 後重新 claim

- **WHEN** work item 經 `abandon` 後以相同 authority 組成重新 claim
- **THEN** claim 成功，不被 `persisted-block` 短路

#### Scenario: 既有 blocked run 不受影響

- **WHEN** registry 中存在未帶釋放標記的既有 blocked run
- **THEN** 其行為維持不變，不回溯改變歷史狀態

### Requirement: 恢復動作必須可稽核且冪等

每次恢復動作 MUST 記錄觸發者、判定為可恢復的依據、恢復前後 run 狀態，且相同恢復請求重送 MUST NOT 產生第二個 planning job 或 run。

#### Scenario: 重送恢復請求

- **WHEN** 相同的恢復請求（含相同 `expected_run_id`）被重送
- **THEN** 不產生第二個 planning job 或 run
- **THEN** 稽核紀錄可看出觸發者與判定依據
