---
status: accepted
work_item: fix-systemctl-install-failure-delivery-v3
---

## Context

`install_service_result()` 先寫入三個 unit 與 manager env，再探測 systemd。systemd 不可用時已有穩定的 `InstallServiceResult(mode="fallback", exit_code=0)`；但 systemd 可用後的 `daemon-reload` 與兩個 `enable` 使用 `check=True`，任何非零狀態都越過結果契約並拋出 traceback。Porcelain `cortex service install` 已能依 `InstallServiceResult.exit_code` 正確輸出文字或 JSON，因此修復應留在 deploy installer 邊界，不新增跨層例外處理。

## Goals / Non-Goals

**Goals:**

- systemctl 非零狀態一律轉成 `InstallServiceResult`，保留 `mode="systemd"` 並使用非零 exit code。
- 訊息指出失敗步驟、systemd stderr、unit 已落檔的位置與直接可執行的重試命令。
- 純文字與 JSON CLI 都不產生 traceback。
- systemd-unavailable fallback 的 mode、exit code、訊息與檔案行為不變。
- 只傳遞 systemd stderr；不得附上 exception repr、環境、stdout 或非必要路徑。

**Non-Goals:**

- 不自動修復 systemd 搜尋路徑、mask、權限、SELinux 或 degraded user manager。
- 不 rollback 已寫入的 unit/env；這些檔案是可恢復安裝的必要輸出。
- 不改 `service start/stop/restart`、unit template 或 systemd availability probe。
- 不新增 retry、timeout 或 shell 執行。

## Decisions

### 1. 以 `check=False` 的 installer-local helper 執行每個 systemctl step

新增私有 helper，固定使用 typed argv、`check=False`、`capture_output=True`、`text=True`。呼叫端依序執行 `daemon-reload`、monitor enable、manager timer enable，遇到第一個非零 return code 即停止並回傳失敗結果。

相較於保留 `check=True` 再捕捉 `CalledProcessError`，這個方案讓「非零是資料，不是例外」成為明確控制流，也可直接檢查每一步 argv 與 capture contract。相較於重用 porcelain 的 `_run_systemctl`，installer-local helper 不會形成 deploy→CLI 的反向依賴。

### 2. 失敗仍屬 `systemd` mode

`mode` 描述安裝所處的 runtime backend，不描述成功與否；成功由 `exit_code` 表示。因此 systemctl 可用但 reload/enable 失敗時保持 `mode="systemd"`，避免擴充既有三態公開契約。exit code 使用失敗 command 的正整數 return code；防禦性地將非正數正規化為 1。

### 3. 錯誤訊息採固定骨架加最小 stderr

訊息固定包含：

1. `systemctl <stage> 失敗`
2. `stderr: <trimmed stderr>`；stderr 為空時使用固定 fallback
3. `unit 已落檔於 <unit_dir>，僅 systemd reload/enable 未完成`
4. 依 stage 給出 `systemctl --user daemon-reload` 或對應 `enable <unit>` 重試命令

不插入 `CompletedProcess`／exception repr、stdout、HOME 以外路徑、環境變數或 command object。`unit_dir` 是 issue 明定的必要資訊。

### 4. 在 installer 與 porcelain 兩層驗證

Installer tests 參數化三個失敗 stage，證明第一個失敗即停止、capture flags 正確、result 結構與檔案落地；另保留既有 fallback regression。Porcelain tests 驗證 JSON 與文字模式以同一非零 exit code 結束、顯示 stderr、無 traceback。

## Risks / Trade-offs

- [Risk] systemd stderr 本身可能包含任意系統文字。→ 僅採 stderr 且 trim，不附 stdout、env 或 exception repr；這是 issue 要求的實際診斷來源。
- [Risk] 第一個失敗後不嘗試後續 enable，可能少收集其他錯誤。→ fail-fast 可維持確定性，使用者修正後重跑 install 即可冪等續行。
- [Risk] unit 已寫入但 enable 未完成是部分成功。→ 訊息與非零 exit code同時表達，不 rollback 可恢復產物，也不回報假成功。

## Migration Plan

無資料遷移。升級後重新執行原 `cortex install service` 或 `cortex service install` 即可；unit/env 寫入與 enable 皆保持冪等。若需 rollback，只需回退程式版本，既有 unit 不受影響。

## Open Questions

無。
