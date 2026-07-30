## ADDED Requirements

### Requirement: card 必須能宣告執行所需 capability

每張 card MUST 能以資料（而非程式碼分支）宣告其執行所需 capability，至少涵蓋 interpreter／module、CLI executable、PTY／bridge dependency 與 network／provider requirement。新增 card MUST NOT 需要修改 preflight 實作即可被檢查。

#### Scenario: 新增 card 的 capability 檢查

- **WHEN** 新增一張宣告了 interpreter module 與 executable 需求的 card
- **THEN** preflight 依宣告逐項檢查，不需修改 preflight 實作

### Requirement: preflight 必須在實際 executor 環境執行

dispatch 前 MUST 於即將實際被使用的 executor environment 執行低成本 preflight，且 MUST 使用與正式 job 相同的 interpreter、`PATH`、`HOME`／sandbox policy 與 provider identity；MUST NOT 只檢查 host `PATH`。preflight 失敗時 MUST NOT 建立 model session。

#### Scenario: host 有而 executor 環境沒有

- **WHEN** host Python 有 `pytest` 但 card 實際使用的 interpreter 沒有
- **THEN** preflight 判定為 capability missing
- **THEN** 不建立 model session，model invocation count 維持 0

#### Scenario: 缺少必要 executable

- **WHEN** reviewer sandbox 缺少 `socat`
- **THEN** dispatch 前即攔截並回傳可操作的原因

### Requirement: provider snapshot 必須帶新鮮度語意

provider snapshot MUST 帶 `observed_at`、TTL、來源與 reason。超過 TTL 的 degraded 判斷 MUST NOT 被直接當成當前事實。系統 MUST 能區分 capability missing、provider unavailable、stale snapshot、probe inconclusive 四種結果。live probe MUST 有 timeout、快取與 rate-limit 預算。

#### Scenario: stale degraded 不硬擋

- **WHEN** provider snapshot 標示 degraded 但已超過 TTL
- **THEN** 不將其視為當前事實，必要時執行有界 live probe

#### Scenario: probe 預算

- **WHEN** 同一批次中多張 card 需要同一 provider 的健康狀態
- **THEN** live probe 依 provider identity 快取，不重複探測
- **THEN** probe 受 timeout 與 rate-limit 預算約束

### Requirement: preflight 失敗優先 re-route

有可替代 identity（capability 相符且 independence domain 合法）時 MUST 自動 re-route；無替代時 MUST 進入帶具體 reason 的 needs_human。status／inspect MUST 顯示缺少的 capability、使用中的 executor environment 與 snapshot 新鮮度。

#### Scenario: 有替代 identity

- **WHEN** preflight 判定當前 identity 缺少必要 capability，且存在合法替代
- **THEN** 自動 re-route 至替代 identity，仍滿足 capability 與 independence domain 規則

#### Scenario: 無替代 identity

- **WHEN** 無任何合法替代 identity
- **THEN** 進入 needs_human 並帶具體 reason
- **THEN** status 顯示缺少的 capability 與使用中的 executor environment
