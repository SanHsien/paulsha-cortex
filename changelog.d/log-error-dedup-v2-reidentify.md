### Changed
- **work item `fix-log-error-dedup` 重識別為 `-v2`**：v1 的三個 run 世代全數消耗於基礎設施缺陷（#390/#397/#399/#401），觸發 #218 語意重宣告熔斷（`semantic-reclaim-budget-exhausted`）；依熔斷設計的逃生門改用新識別，issue 374 連結與 workstream todo 隨遷。此案例同時佐證 #331（-v2 重識別摩擦）所述成本。
