---
status: accepted
work_item: per-work-model-chain
---

# per-work-model-chain Design

## Decisions

### D1 覆寫存在 run 記錄，不進共享 registry

run-scoped 覆寫寫入 WorkflowRun 的欄位，`_select_workflow_identity` 在選擇前先檢查該欄位。共享 `model-identities.yaml` 完全不動。

理由：問題的本質是「run 層的意圖被存在全域層」。把覆寫放回 run 層即從根本消除跨 run 干擾，也不需要為 dogfood 反覆改寫共享設定檔。

### D2 覆寫於 claim 時凍結，比照 authority 凍結

覆寫值在 claim（或首次 dispatch）時寫入 run 並視為凍結輸入，後續動作讀凍結值。

理由：repo 既有的 authority／pinned inputs 就是這個模式——claim 當下凍結，之後所有 phase 讀同一份。模型鏈屬於同一類「這次 run 的決定」，用同一套語意可避免 operator 需要記兩種規則。

### D3 三段各自可獨立覆寫，未指定者回退共享 registry

planner／builder／reviewer 三段各自獨立；未指定的那一段回退既有共享 registry 選擇。

理由：實務上常見只想換 builder（例如指定 codex/spark 做實作）而 planner／reviewer 維持預設。強制三段全指定會讓常見情境變麻煩，也增加打錯的機會。

### D4 覆寫不放寬既有約束，違反即 fail closed

覆寫的 identity 一樣要過 capability 檢查與 builder／reviewer independence domain 不同的規則；不符即拒絕並回報原因，不靜默退回預設。

理由：覆寫是「指定用哪一個合法選項」，不是「跳過檢查」。靜默退回是最糟的行為——operator 以為指定生效，實際跑的是別的模型，且事後從結果看不出來。

### D5 解析結果與來源一併寫入 evidence

evidence 記錄三段各自的 executor、model，以及來源標記（run-scoped override / shared registry）。

理由：只記模型名不足以稽核——同樣是 `gpt-5.3-codex-spark`，「operator 指定的」與「剛好排在共享 registry 第一個」是兩件事。來源標記讓事後能判斷結果是否反映當時意圖。

## 風險與緩解

- **覆寫欄位與既有 run schema 相容性**：比照 `retry_classification`／`pr_candidate` 等既有可選欄位的加法，provenance-only 欄位排除在 semantic match 之外，避免良性差異觸發衝突判定。
- **operator 指定了不存在的 model**：fail closed 並列出該 capability 下可用的 identity，讓錯字可以立刻看出來。
- **凍結值在長時間 run 中過時**：提供明確的再次覆寫路徑（operator 顯式操作），而非自動漂移回共享 registry。
