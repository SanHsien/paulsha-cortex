---
status: accepted
work_item: dispatch-runtime-preflight
---

# dispatch-runtime-preflight Design

## Decisions

### D1 capability 以資料宣告，preflight 是通用執行器

card／persona contract 增加 capability 宣告欄位（interpreter module、executable、bridge、provider），preflight 讀宣告後逐項檢查，不為個別 card 寫分支。

理由：#262 觀察到的三個缺口（pytest、socat、provider）形態不同但檢查成本都很低。若用程式碼分支處理，每加一種 card 就要改 preflight；宣告式讓覆蓋範圍隨 card 定義自然增長。

### D2 preflight 必須在 executor 環境內執行，而非 manager 環境

檢查透過與正式 job 相同的啟動路徑進入 executor environment（相同 interpreter、PATH、HOME／sandbox policy），在其中執行探測。

理由：這是本 issue 的核心。`pytest` 在 host 存在但在 Spark 隔離環境不存在，正說明「在 manager 這側檢查」會給出假通過。檢查環境與執行環境必須是同一個，否則 preflight 只是安慰劑。

### D3 provider 健康採「快照 + TTL + 有界 probe」三層

snapshot 帶 `observed_at`／TTL／source／reason；TTL 內直接採信，逾期則對必要 provider 執行有界 live probe，probe 結果回寫快照。

理由：純快照會讓 stale degraded 永久誤擋（#262 實際遇到）；純 live probe 則每次 dispatch 都付出網路成本並可能觸發 rate limit。三層設計讓常態走快取、只有逾期才付探測成本。

### D4 四種結果分開表達，不合併為布林

capability missing、provider unavailable、stale snapshot、probe inconclusive 各自是獨立結果，不折疊成「可用／不可用」。

理由：四者的正確處置不同——capability missing 要修環境或 re-route；provider unavailable 可等待或換 identity；stale snapshot 要刷新；probe inconclusive 不應被當成失敗。合併成布林會逼呼叫端猜測，也讓 status 顯示不出實際原因。

### D5 preflight 失敗優先 re-route，其次 needs_human

有可替代 identity（capability 相符、independence domain 合法）時自動 re-route；無替代時進入帶具體 reason 的 needs_human。

理由：多數 capability 缺失是特定 executor 環境的問題，換一個 identity 就能繼續。直接 needs_human 會讓可自動處理的情境不必要地停下來等人。

### D6 probe 預算與 preflight 結果共用快取鍵

live probe 的 timeout／cache／rate-limit 預算以 provider identity 為鍵，與 preflight 結果快取共用。

理由：避免同一批次內多張 card 對同一 provider 重複探測，這正是「另一個昂貴 retry loop」的來源。既有 `claim_readiness` 的 live probe TTL 快取已有先例，沿用同一模式。

## 風險與緩解

- **preflight 本身成為新的成本來源**：檢查限於低成本探測（module import、executable 存在性、快取內的 provider 狀態），live probe 有預算上限並共用快取。
- **capability 宣告不完整導致漏檢**：漏檢的後果退回現狀（dispatch 後才失敗），不會比現在更差；status 顯示實際使用的 executor environment，便於事後補宣告。
- **re-route 造成 identity 選擇偏移**：re-route 僅在 capability 檢查失敗時觸發，且必須滿足既有的 capability 與 independence domain 規則，不放寬既有約束。
