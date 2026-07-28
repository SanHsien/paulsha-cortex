## MODIFIED Requirements

### Requirement: systemctl 啟用失敗需轉為可行動、無 traceback 的 structured result

`cortex install service` 與 `cortex service install` 在 systemd 可用但 `daemon-reload`／`enable` 失敗時，`install_service_result()` MUST 回傳 `mode="systemd"` 且非零 `exit_code` 的 result，訊息需固定包含失敗階段、trimmed stderr、unit directory 與可直接重試的 `systemctl --user ...` 指令，並不得外洩 stdout 或 exception repr。

#### Scenario: daemon-reload 或 enable 失敗時的 structured result

- **WHEN** `cortex install service` 在 `daemon-reload`、`enable <instance>-monitor.service` 或 `enable <instance>-manager.timer` 任一步驟回傳非零
- **THEN** command sequence 必須於第一個非零步驟停止並回傳 `InstallServiceResult(mode="systemd", exit_code=returncode)`
- **THEN** message 必須包含失敗步驟、`stderr`、`~/.config/systemd/user`、以及該步驟對應的 `systemctl --user ...` 重試命令
- **THEN** message 不得包含 `CompletedProcess`、`Traceback`、`stdout`、環境變數或其他非必要路徑

#### Scenario: plain 與 JSON CLI 共用同一失敗 contract

- **WHEN** 對同一個非零失敗 stage 執行 `cortex install service` 及 `cortex service install --json`
- **THEN** 兩者皆以相同非零 exit code 結束
- **THEN** plain output 與 JSON output 皆轉出一致的人類可判讀訊息要素，且 JSON message 欄位不含 traceback
