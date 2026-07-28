---
status: accepted
work_item: fix-systemctl-install-failure
---

# Tasks

- [x] [RED] 在 `tests/test_install_service.py` 新增三階段 systemctl 失敗回歸測試（daemon-reload / monitor 啟用 / manager timer 啟用），驗證 `mode=="systemd"`、`exit_code==7`、訊息含 stderr/unit dir/retry command、無 stdout/CompletedProcess/Traceback 且失敗後不再執行後續 command。
- [x] [RED] 在 `tests/test_porcelain_service.py` 加入 plain 與 `--json` 兩條 install 回歸，驗證 exit code 7 與訊息正確且無 Traceback。
- [ ] [RED] 執行 `python3 -m pytest -q tests/test_install_service.py tests/test_porcelain_service.py -k "systemctl and install"`（目前環境缺 pytest，待補齊後執行）。
- [x] [RED] 依序提交紅測試 `test(installer): 新增 systemctl 失敗 regression (#253)`。
