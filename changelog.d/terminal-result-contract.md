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

- **Issue #261（收口）：gate ledger 由 manager 掌控的 wrapper 產生，canonical envelope 實際生效**：
  新增 `paulsha_cortex/coordinator/gate_ledger.py`，由 `launcher.build_wrapper_script` 產生的
  headless wrapper 在模型行程結束**之後**執行——`<模型 argv>; printf %s "$?" > <sentinel>;
  python3 -m ...gate_ledger --out <ledger> --worktree <wt> >/dev/null 2>&1`。三段以 `;` 串接，
  模型失敗時 sentinel 與 ledger 仍會產生；sentinel 早於 gate 階段寫入，模型 exit code 不被
  gate 耗時污染；gate 輸出導向 `/dev/null`，不污染 terminal evidence 解析。gate 清單由 operator
  以 `PSC_GATE_CMD_<NAME>` 宣告（沿用 `PSC_PREFLIGHT_CMD` 的 typed-argv 規範、拒絕 shell wrapper），
  exit code 來自真實 subprocess，模型既不能選 gate、不能定 exit code，也拿不到 ledger 路徑
  （由 job `log_path` 推導、位於 manager 的 log_dir），因此 R2 的重驗不再是「拿模型的話驗模型的話」。
  跑不起來或逾時的 gate 一律記為 `failed`。`_workflow_job_prompt` 改發 `schema_version: 2` 的
  canonical envelope（含 `diagnostics` 與 `gate_evidence`），舊形狀維持相容讀取；build／verify
  的 `passed` 在缺少 ledger 時 fail closed。schema retry 計數經 workflow provider observations
  投影到 Monitor work item envelope，`cortex inspect work` 會列出 `schema_retry[<card>]:
  <count>/<limit>`；計數沿用既有 `attempts` 欄位而非新增 `WorkflowRun` 欄位，避免 #205 那類
  「新欄位讓每個 run row 變 unsupported、整份 projection degraded」的 regression。
