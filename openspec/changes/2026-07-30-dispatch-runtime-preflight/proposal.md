---
status: accepted
work_item: dispatch-runtime-preflight
---

## Goals

在 dispatch 之前、於實際將被使用的 executor 環境中驗證 runtime capability 與 provider snapshot 新鮮度，避免昂貴 job 啟動後才因可廉價預判的條件失敗。

## Why

缺 pytest／socat 這類零成本可測的條件，目前要等到 worktree 與 model session 建立之後才暴露，消耗時間與 token 並留下不完整的 job 與 evidence；stale 的 degraded snapshot 也可能錯誤影響 routing。

## What Changes

- card／persona contract 增加資料驅動的 capability 宣告（interpreter module、executable、bridge、provider）。
- dispatch 前在與正式 job 相同的 executor environment（interpreter、PATH、HOME／sandbox policy、provider identity）執行低成本 preflight；失敗不建立 model session。
- provider snapshot 增加 `observed_at`／TTL／source／reason；逾期時對必要 provider 執行有界 live probe。
- capability missing／provider unavailable／stale snapshot／probe inconclusive 四種結果各自獨立表達。
- 有合法替代 identity 時 re-route，否則進入帶具體 reason 的 needs_human；live probe 預算與 preflight 快取共用鍵。

## Capabilities

### Modified Capabilities
- 詳見 `docs/superpowers/specs/dispatch-runtime-preflight-spec.md` 的 Requirements 與 `docs/superpowers/specs/dispatch-runtime-preflight-design.md` 的 Decisions。
