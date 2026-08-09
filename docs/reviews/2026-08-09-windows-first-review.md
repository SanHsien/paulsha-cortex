# Windows-first repository review — 2026-08-09

## 結論

狀態：**Windows development ready；production readiness 仍為 NEEDS WORK。**

本輪 review 覆蓋整個 Python package、service/install、coordinator launcher、monitor transport、workflow/review evidence、file durability、path/mode semantics 與完整測試套件。原生 Windows 基線從 collection 階段 28 errors，改善到首次可跑全套時的 100 failures，再收斂為 `2002 passed, 72 skipped, 2 failed, 32 subtests passed`；最後兩個 registry backup failures 也已修復。

Production 尚未放行的理由不是 native Windows correctness，而是 upstream 在本次水位仍沒有 LICENSE，以及 bubblewrap foreign-review sandbox 仍是 Linux-only。兩者不得被 CI 綠燈取代。

## Findings 與處置

| 嚴重度 | Finding / root cause | 修正 |
| --- | --- | --- |
| P0 | Windows 上用 `os.kill(pid, 0)` 探測 PID 會實際送出 signal，可能終止 pytest/manager/tool host。 | 新增 non-mutating `pid_exists()`；Windows 用 `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)`，manager 另以 CIM command line 驗證身份。 |
| P1 | `fcntl`、`os.getloadavg`、`O_DIRECTORY` 在 import/collection 或 durability 路徑直接假設 POSIX。 | 新增 lazy file-lock、safe load-average 與 directory-fsync adapters；Windows 分別採 `msvcrt`、safe fallback、no-op durability boundary。 |
| P1 | Agent launcher 以 Bash wrapper/shell string 執行，Windows 無法可靠啟動或保存同一 Candidate 的 sentinel/gate evidence。 | 新增 typed-argv Python process wrapper；先 durable 寫 exit sentinel，再執行 gate ledger。 |
| P1 | Monitor 固定使用 Unix socket。 | Linux 保留 AF_UNIX；Windows 使用 loopback TCP，endpoint 以 atomic JSON manifest 發布。 |
| P1 | Windows 對剛關閉的 loopback listener 可能回 connect timeout 而非 refused；若直接刪 manifest 會搶走 live endpoint，若一律拒絕又無法 crash recovery。 | timeout 後以 `SO_EXCLUSIVEADDRUSE` 探測 port owner；只有確認無 owner 才回收 manifest，否則 fail-closed 拒絕第二個 monitor。 |
| P1 | Service lifecycle 只支援 systemd/fallback shell，Windows 的 install/start/stop/restart/uninstall 全不可用。 | 新增不需提權的 per-user Startup backend、manifest、PID/lock、hidden detached processes、身份驗證後的安全 stop/restart 與 log。Task Scheduler 在非提權環境拒絕註冊，因此不列為 Windows 依賴。 |
| P1 | Evidence hash、authority snapshot 與 idempotency 直接比較 CRLF/LF bytes，跨平台會把同一 Candidate 誤判為不同。 | 對 workflow authority content 做 canonical EOL 比較，並同時接受可證明等價的 raw/LF/CRLF hashes。 |
| P1 | Immutable evidence/backup 在 Windows 先 chmod hardlink，read-only attribute 會讓暫存名稱無法 unlink；反之 POSIX 若 link 後才 chmod，崩潰窗口會留下可寫 evidence。 | POSIX 採 chmod source → link，確保 evidence 發布瞬間即唯讀；Windows 採 link → unlink temp name → chmod retained target。兩邊皆收斂為 owner-read-only `0400`。 |
| P1 | Monitor 在 parent listing 後遇到矛盾的 transient stat 結果，會把健康 snapshot 當成 authoritative removal。 | 矛盾狀態標為 degraded，保留 last-good project state。 |
| P2 | `Path.is_absolute()`、mode bit、HOME、subprocess encoding 與 cleanup 邏輯混用 host-specific semantics。 | 新增 host-independent path safety、Windows permission equivalence、HOME/USERPROFILE handling、UTF-8 Git decoding 與 read-only tree cleanup。 |
| P2 | 測試會寫入真實使用者 `.agents`，並把 POSIX shell/systemd integration 當成 Windows native test。 | 隔離 runtime roots；Windows 執行核心全套，POSIX-only sandbox/shell integration 明確 skip 並由 Linux CI 覆蓋。 |

## Windows 驗收清冊

- [x] 原生 pytest 可 collection 並跑完整 package。
- [x] manager PID probe 不會對被探測程序送 signal。
- [x] launcher 以 typed argv 執行，不依賴 Bash。
- [x] monitor server/client 在 Windows 以 loopback TCP 通訊。
- [x] workflow authority/review evidence 對 CRLF/LF 保持 Candidate identity。
- [x] immutable evidence 與 v1 backup 可在 Windows 建立、清理與驗證。
- [x] service installer/lifecycle 有不需管理員權限的 Windows backend。
- [x] PowerShell bootstrap、quick/full gate 與 Windows GitHub Actions job 已建立。
- [x] README、Development、Fork、Decisions 與 upstream tracking 已改為 Windows-first。

## 明確保留的限制

- `bubblewrap`/`socat` foreign-review sandbox 仍只在 Linux 提供；Windows skip 不代表 sandbox 通過。
- Git symlink 行為仍取決於 Windows Developer Mode；policy mirror 檔不可在退化 checkout 中編輯。
- upstream 授權未明前，不把本 fork 當成已取得完整再散布授權的 production 發行版。

## 驗證證據

- 原生 Windows focused suites：installer/service、launcher、monitor、workflow production、work bridge、path/mode/process/durability regressions 均通過。
- 原生 Windows full suite（修復前最後清單）：`2002 passed, 72 skipped, 2 failed, 32 subtests passed in 302.49s`；僅剩的兩項同源 registry backup ordering bug 已由 `tests/test_workflow_registry.py` 的 `16 passed` 證明修復。
- PowerShell bootstrap 在僅有 Python 3.14、`py -3.13` 不存在的主機完成 `.venv` 與 dev dependencies 安裝；quick gate 為 `14 passed`。
- 唯一 live service smoke `cortex-smoke-20260809`：隔離 HOME/APPDATA 下 install 成功，manager/monitor PID 在第二次 status 仍為 running，stop 後兩者歸零，uninstall/purge 成功；smoke 目錄已移至資源回收筒。
- PR 首輪 Ubuntu CI 找到三個跨平台回歸：typed wrapper 後的 launcher 測試仍檢查舊 shell token、Unix monitor probe 未走 transport seam、POSIX immutable evidence 的 chmod/link 次序有崩潰窗口。三項均已修復；同輪 CodeQL 指出的 lock/evidence 權限與 `ctypes` import finding 亦已修復。
- Ubuntu 3.10/3.11 matrix 另驗出 `shutil.rmtree(onexc=...)` 僅存在於 Python 3.12+；filesystem adapter 已依版本在舊 Python 使用 `onerror`，並以模擬 3.11 分支的 regression test 固定相容性。
- 最終 Windows gate：`pwsh -File tools/dev_check.ps1` 通過，結果為 `2005 passed, 72 skipped, 32 subtests passed in 320.20s`；wheel/sdist build 成功，兩個 artifacts 的 `twine check --strict` 均為 PASSED。此 bullet 是 gate 後追加的文件 evidence，不改 runtime/package input。
