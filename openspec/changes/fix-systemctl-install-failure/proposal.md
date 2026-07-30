---
status: accepted
work_item: fix-systemctl-install-failure-delivery-v3
---

## Why

`cortex install service` 已成功寫入 systemd unit 後，只要 `daemon-reload` 或任一 `enable` 回傳非零，就會將未處理的 `CalledProcessError` traceback 直接暴露給使用者。這既遮蔽 systemd 真正的 stderr，也讓使用者無法判斷 unit 已落檔、只差啟用步驟。

## Goals

- 將所有 service install systemctl 非零狀態收斂為結構化、可行動且無 traceback 的結果。
- 保留 systemd stderr 與必要 unit directory，同時限制輸出邊界。
- 維持既有 systemd-unavailable fallback 與成功路徑相容。

## What Changes

- 將 install 階段的三個 systemctl 呼叫改為可觀測的 typed argv 執行，捕捉 stderr 與 return code。
- 第一個失敗步驟回傳結構化 `InstallServiceResult`，以非零 exit code 結束而不拋 traceback。
- 失敗訊息明確指出失敗 stage、systemd stderr、已落檔的 unit directory，以及可執行的重試步驟。
- 保持 `_systemctl_available() == False` 的既有 fallback mode、訊息與 exit code 不變。
- 新增 installer 與 porcelain CLI regression，涵蓋 daemon-reload、兩個 enable、純文字與 JSON 輸出，以及資訊邊界。

## Capabilities

### New Capabilities

無。

### Modified Capabilities

- `porcelain-service-lifecycle`: service install 的 systemd 啟用失敗必須結構化回報，不得產生 traceback 或假成功。

## Impact

- 修改 `paulsha_cortex/deploy/installer.py` 的 systemctl install 執行與結果組裝。
- 驗證 `paulsha_cortex/porcelain/service.py` 既有 `InstallServiceResult` 包裝能正確傳遞非零 exit code。
- 擴充 `tests/test_install_service.py` 與 `tests/test_porcelain_service.py`。
- 更新 `CHANGELOG.md`、精確 change-slug fragment 與必要的 service 操作文件。
- 不新增依賴、不改 unit 內容、不改 fallback 啟動契約。
