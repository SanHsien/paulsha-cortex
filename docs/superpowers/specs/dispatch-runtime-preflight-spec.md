---
status: accepted
work_item: dispatch-runtime-preflight
---

# dispatch-runtime-preflight Specification

#262：在 dispatch 之前、於實際將被使用的 executor 環境中驗證 runtime capability 與 provider snapshot 新鮮度，避免昂貴 job 啟動後才因可廉價預判的條件失敗。

## 背景

2026-07-30 auto-run dogfood #252～#254 時，數個可在 dispatch 前廉價判定的條件，直到 executor／reviewer session 啟動後才暴露：

- Spark 的隔離執行環境缺少 `pytest` module，雖然 host/system Python 有 pytest；card 實際使用的 interpreter 無法執行 repo 全套測試。
- reviewer sandbox 所需的 `socat` 不存在，review 路徑因此降級／停用。
- provider snapshot 一度標示 rate-limit／degraded，但 live capacity 仍可使用；stale 或錯誤快照可能錯誤影響 routing。

上述失敗都發生在 worktree／model session 已建立之後，消耗時間與 token，並留下不完整的 job 與 evidence。

#255／#256 處理的是 planning identity 的正規化與不可恢復 claim；本 issue 聚焦的是 **card 實際 runtime capability 與 provider health 的新鮮度**。

## Goals

- 可廉價預判的失敗在 dispatch 前攔截，model invocation 維持 0。
- preflight 的執行環境與正式 job 一致，不因檢查環境與執行環境不同而產生假通過。
- provider 健康判斷帶新鮮度語意，stale 的 degraded 判斷不被當成當前事實。

## Requirements

### R1 card 宣告必要 capability

每張 card SHALL 能宣告其執行所需的 capability，至少涵蓋：interpreter／module、CLI executable、PTY／bridge dependency、network／provider requirement。

宣告 MUST 是資料而非程式碼分支，使新增 card 不需修改 preflight 實作即可被檢查。

### R2 preflight 在實際 executor 環境執行

dispatch 前 SHALL 於「即將實際被使用的 executor environment」執行低成本 preflight。

preflight MUST 使用與正式 job 相同的 interpreter、`PATH`、`HOME`／sandbox policy 與 provider identity；MUST NOT 只檢查 host `PATH`。

preflight 失敗時 MUST NOT 建立 model session，並 MUST 回傳可操作的 re-route 或 needs_human 原因。

### R3 provider snapshot 帶新鮮度

provider snapshot SHALL 帶 `observed_at`、TTL、來源與 reason。

超過 TTL 的 degraded 判斷 MUST NOT 被直接當成當前事實；對必要 provider MAY 執行有界的 live probe。

系統 MUST 能明確區分四種結果：capability missing、provider unavailable、stale snapshot、probe inconclusive。

### R4 probe 成本有界

live probe MUST 有 timeout、快取與 rate-limit 預算，不得形成另一個昂貴的 retry loop。

### R5 可觀測

status／inspect MUST 顯示缺少的 capability、使用中的 executor environment、以及 snapshot 新鮮度。

## 非目標

- 不改 identity 選擇順序與 independence domain 規則。
- 不實作 per-work 模型鏈覆寫（屬 #205 範圍）。
- 不改 terminal/result contract（屬 #261 範圍）。

## 驗收面

- 缺 `pytest`／`socat` 的 fixture 在 dispatch 前被攔截，model invocation count 維持 0。
- preflight 與正式 job 使用相同 interpreter、PATH、HOME／sandbox policy 與 provider identity。
- 有可替代 identity 時可安全 re-route；無替代時進入帶具體 reason 的 needs_human。
- snapshot 含 `observed_at`／TTL／source／reason，stale degraded 不被當成 fresh hard block。
- live probe 有 timeout／cache／rate-limit 預算。
- status／inspect 顯示缺少的 capability、executor environment 與 snapshot 新鮮度。
