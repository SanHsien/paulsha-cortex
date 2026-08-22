# Admin

這份文件整理日常維運時最常用的命令，目標是先用 `service` / `inspect` / `request` 家族看真相，再決定是否需要 recovery。

## 引用來源

- `docs/superpowers/specs/2026-07-21-porcelain-cli-ux-design.md` §6
- `docs/superpowers/specs/onboarding-docs-spec.md`
- `docs/superpowers/specs/porcelain-service-spec.md`
- `docs/superpowers/specs/porcelain-inspect-spec.md`
- `docs/superpowers/specs/porcelain-request-spec.md`
- issue #94
- `python3 -m paulsha_cortex.cli service --help`
- `python3 -m paulsha_cortex.cli inspect --help`
- `python3 -m paulsha_cortex.cli request --help`

## 日常檢查

```bash
cortex service status --instance cortex --json
cortex inspect service --instance cortex --json
cortex inspect doctor --json
cortex status
cortex list --repo owner/name --state on-going --explain
```

重點：

- `cortex service ...`：看 service/runtime/logs 與 start/stop/restart
- `cortex inspect ...`：唯讀查詢 status/job/ready/work/doctor/service
- `cortex status`：看 manager 目前 gate 與 slice 狀態
- `cortex list`：看跨來源投影出的 work read model

## 常用操作

### service

```bash
cortex service start --instance cortex
cortex service restart --instance cortex
cortex service logs --instance cortex -n 50
cortex service uninstall --instance cortex --json
```

### inspect

```bash
cortex inspect ready --json
cortex inspect work <work-id> --repo owner/name --json
cortex inspect job <job-id>
cortex inspect models --json
```

### request

```bash
cortex request list
cortex request show <request-id>
cortex request wait <request-id> --timeout 30
```

## Model profiling

`cortex inspect models` 會顯示目前 model identity × persona 的能力封套，以及每個欄位是實測值或保守預設值。沒有選配的 `patchmud` 時，Cortex 會維持保守預設，不把缺少評測誤報成已驗證能力。

需要建立或更新實測封套時：

```bash
cortex model profile
cortex model profile --apply
cortex model profile --force
```

- `cortex model profile`：偵測可用 adapter、執行評測並預覽差異，不寫入 registry。
- `--apply`：人工複核後套用實測封套。
- `--force`：忽略既有評測指紋，強制重跑。

評測指紋會包含 executor、model identity、persona、deck、deck content hash 與 patchmud version；指紋未變時可直接重用既有結果。adapter 不可用的 model 必須維持預設封套並回報 unavailable，不得假造實測結果。

## Digest delivery

`cortex digest emit` 會產生目前工作面的 digest，預設先寫入本機 outbox；若需要交給外部通知腳本，使用 `PSC_DIGEST_DELIVERY_CMD` 明確設定 delivery command。

```bash
cortex digest emit
```

delivery command 以 typed argv 執行，不經 shell interpolation；digest payload 走 stdin，而不是塞進 command line。外部 delivery 失敗時應保留本機 evidence 並回報失敗，不把「有執行 command」當成已送達。

正式部署前應另外驗證 delivery command 的 timeout、exit status、輸入大小與敏感資訊處理；不要把通知通道當成 lifecycle authority。

## 建議的日常節奏

1. 先看 `cortex service status --json`，確認 manager 在不在、跑在哪個 mode。
2. 再看 `cortex inspect service --json`，確認執行中的版本與 `venv` 沒漂移。
3. 有 mutation 剛送出時，看 `cortex request ...`，不要只盯著終端機是否 timeout。
4. 要查跨 repo 工作面時，改看 `cortex list` / `cortex work show`。

## 什麼情況要升級或回滾

- `inspect service` 抓到 stale `venv`
- service restart 後仍持續 `manager degraded`
- 同一版 CLI 反覆出現 request timeout、或行為與 release note 不一致

這時先轉去 [Upgrade](upgrade.md) 或 [Rollback](rollback.md)，不要把日常維運操作硬當成修復流程。
