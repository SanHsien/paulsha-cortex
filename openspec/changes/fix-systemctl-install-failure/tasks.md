---
status: accepted
work_item: fix-systemctl-install-failure
---

# Tasks

- [x] [GREEN] 新增 installer 內部 `systemctl` 失敗結構化處理 helper：
  - `test install result` 的 `check=False` 與 `capture_output=True` 實作
  - 首個非零返回步驟立即返回 `InstallServiceResult(mode=\"systemd\", exit_code!=0)`
  - 失敗訊息只保留 systemd stderr、unit directory 與重試 command
- [x] [RED] 在 `tests/test_install_service.py` 新增三階段 systemctl 失敗回歸測試（daemon-reload / monitor 啟用 / manager timer 啟用），驗證 `mode=="systemd"`、`exit_code==7`、訊息含 stderr/unit dir/retry command、無 stdout/CompletedProcess/Traceback 且失敗後不再執行後續 command。
- [x] [RED] 在 `tests/test_porcelain_service.py` 加入 plain 與 `--json` 兩條 install 回歸，驗證 exit code 7 與訊息正確且無 Traceback。
- [x] [GREEN] 依序加入/通過 `tests/test_install_service.py`、`tests/test_porcelain_service.py` 的 systemctl 回歸測試；全域 `pytest` 維持綠燈（含 `-k systemctl and install` 與完整 suite）。
- [x] [RED] 依序提交紅測試 `test(installer): 新增 systemctl 失敗 regression (#253)`。
- [x] [GREEN] 更新 `CHANGELOG.md`（`[Unreleased]`）與 `changelog.d/fix-systemctl-install-failure.md`。
- [x] [GREEN] 在 service 安裝文件補齊 `daemon-reload`/`enable` 非零時的使用者回報行為。
