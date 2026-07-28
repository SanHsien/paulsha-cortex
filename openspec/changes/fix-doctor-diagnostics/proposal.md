---
status: accepted
work_item: fix-doctor-diagnostics-delivery
---

## Why

`cortex doctor` 在必要 runtime contract 不成立時，把底層可執行原因收斂成泛化錯誤；fresh install 因未設定 `PSC_PREFLIGHT_CMD` 直接失敗，卻無法從 CLI 或 onboarding 文件得知修復方式。這讓原本應縮短排障時間的 doctor 反而成為沒有下一步的紅燈。

## What Changes

- doctor 的 preflight 與 model-identity probes 保留經清理的底層 reason，至少可區分 required、malformed 與 executable-unavailable。
- 診斷文字提供可執行下一步，同時避免輸出 secret、命令 payload 或不必要的個人絕對路徑。
- README 補上 `PSC_PREFLIGHT_CMD` 的用途、argv JSON 格式與 shareable-safe 範例。
- onboarding quickstart 在第一次執行 doctor 前設定必要變數；troubleshooting 補上對應 FAIL 的排除流程。

## Capabilities

### New Capabilities

- `actionable-doctor-diagnostics`: 規範 required runtime contract 失敗時的分類、可執行訊息與敏感資訊邊界。

### Modified Capabilities

- `onboarding-documentation`: fresh install 文件必須在 doctor 前交代 `PSC_PREFLIGHT_CMD`，並提供此 FAIL 的排除步驟。

## Impact

- 受影響程式：`paulsha_cortex/doctor.py` 與既有 doctor tests。
- 受影響文件：`README.md`、`docs/onboarding/quickstart.md`、`docs/onboarding/troubleshooting.md`。
- CLI exit code 與 probe requiredness 不變；只改善診斷細節與文件契約。
