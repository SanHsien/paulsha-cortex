### Fixed
- **Issue #261：terminal/result contract 誠實表達 gate failure，消除 fail-open 破口**：
  新增 `paulsha_cortex/coordinator/terminal_contract.py` 作為 terminal/result 契約的單一
  真相源——帶 `schema_version` 的 canonical envelope 讓 `passed`／`failed`／`needs_human`
  三種終局狀態在 build／verify／review 三類 card 上對等可達，舊形狀 payload 走相容讀取
  路徑並帶 legacy 標記（不拒收既有 run）。`terminalize_workflow_job` 在任何狀態採信之前
  先做確定性 cross-check：manager 重讀自己 evidence 目錄下的 gate ledger，只要有任何
  gate 實際失敗（含 ledger 自身矛盾，例如記了非 0 exit code 卻標 passed），terminal 自稱
  的 `passed` 一律 fail closed，並保留「哪一個 gate、期望值、實際值」的可操作原因；模型
  文字、exit code 為 0、無明確錯誤三者皆不再構成成功授權。StructuredOutput 的 wrapper
  正規化改採明確白名單且同一確定性 mismatch 只嘗試一次，未知形狀終止為可操作錯誤而非
  被寬鬆解析吞掉；`resume_workflow_run` 的 malformed-terminal 重派改為有上限、有計數器
  （持久化於 `run.attempts`，逾限轉 `needs_human` 並回報 `schema_retry_count`／
  `schema_retry_limit`／`last_validation_path`／`last_validation_reason`），終結同一格式
  錯誤反覆回派模型的 retry storm。terminal parse 失敗時保留 observed HEAD／job id／
  失敗原因的唯讀診斷，但與授權欄位分離儲存，可觀測不等於可授權。verifier 與 reviewer 的
  StructuredOutput schema 與 prompt contract 同步放開非通過狀態，非通過狀態由 manager
  fail closed 為可操作錯誤，而不是被誤判成 schema 壞掉。
