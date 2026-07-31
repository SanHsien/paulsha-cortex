### Fixed
- **Issue #277：repo rebind 後 monitor 投影與 work authority 跟隨 `PSC_REPO_ROOT`**：
  - monitor 設定解析遇到 deprecated legacy 設定（`PAULSHACLAW_CONFIG` 或 `paulshaclaw.yaml`）時改為 fail-loudly 拋出 `ValueError`，不再靜默降級至舊 repo 設定。
  - monitor config 載入時自動將 `PSC_REPO_ROOT` 納入監控專案集，確保 instance 換綁 repo 後 monitor 投影能正確解析當前 repo 的 work items。
  - `work link` / `unlink` 重寫 `.cortex/work-items.yaml` 時保留原始鍵（key）排序，避免無謂重排導致 git status 變 dirty，並於寫入後新增 readback 讀回驗證。
