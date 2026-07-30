---
status: accepted
work_item: fix-doctor-diagnostics-delivery
---

## Context

`doctor._preflight_probe()` 與 `_identity_probe()` 目前攔截 runtime validator 的 `ImportError`、`OSError`、`ValueError`，但固定回傳 `runtime validator rejected ...`。底層 preflight validator 已提供 required、malformed、shell-wrapper 與 executable-unavailable 等穩定分類；直接丟棄會讓使用者無法修復，直接原樣顯示又可能洩漏命令內容或個人絕對路徑。README 與 onboarding 也沒有在第一次 doctor 前建立 `PSC_PREFLIGHT_CMD`。

## Goals / Non-Goals

**Goals:**

- 讓 preflight probe 的 FAIL 明確區分 required、malformed、shell-wrapper 與 executable-unavailable，並給出可執行下一步。
- 讓 model-identity probe 至少保留 missing、unreadable、schema/contract-invalid 等穩定分類。
- 所有 detail 都由 allowlisted category 與固定文案產生，不回顯 exception 中的任意值。
- 在 README、quickstart、troubleshooting 建立一致且 shareable-safe 的設定／排障路徑。

**Non-Goals:**

- 不改 `PSC_PREFLIGHT_CMD` 的 typed argv、禁止 shell wrapper或 executable resolution 契約。
- 不改 doctor probe 的 requiredness、exit code、JSON schema 或 probe 名稱。
- 不在此變更提供預設 preflight command，亦不弱化 fail-closed 行為。

## Decisions

1. **以 allowlist 分類器轉譯例外，不直接輸出 `str(exc)`。**
   preflight 與 identity 各自維持小型純函式，依穩定前綴／例外類型回傳固定 detail；任何未知錯誤回到不含 payload 的 `validator unavailable/invalid`。相較直接 regex 刪路徑，allowlist 能同時避免 secret、argv 與未預期格式外洩。

2. **訊息同時包含分類與下一步。**
   required 指向設定 `PSC_PREFLIGHT_CMD`；malformed 指向 shell-style argv quoting；shell-wrapper 指向直接 typed executable；executable-unavailable 指向安裝 executable 或改用 PATH 可解析命令。identity 則指向 `PSC_PROJECT_CONFIG_ROOT/model-identities.yaml` 的存在性、可讀性或 schema 修正。

3. **文件只使用抽象 executable 範例。**
   README 與 onboarding 使用 `export PSC_PREFLIGHT_CMD='python3 -m project_preflight'` 作為純格式示例，並明示必須替換成 repo 實際提供的 module；不得放入個人路徑、token 或特定私有工具名稱。

4. **測試直接覆蓋分類器與 public probe detail。**
   先寫 RED regression，以 monkeypatch 讓 runtime validator 產生每一類錯誤；測試同時斷言分類存在、下一步存在，以及 secret marker／absolute path 不存在。

## Risks / Trade-offs

- **底層錯誤字串改名會落入 generic fallback** → 測試鎖定 runtime validator 現行訊息，未知類型仍安全且 fail-closed。
- **固定文案可能少於原始 traceback 細節** → doctor 面向 operator 提供安全分類；完整開發除錯仍由直接 validator invocation 或受控 log 承擔。
- **文件範例無法代表每個 repo 的實際 preflight 工具** → 明確標示 placeholder 必須換成專案提供的 executable，避免虛構通用命令。

## Migration Plan

此變更不需資料遷移。升級後既有有效設定維持 PASS；無效設定得到更具體但同樣 fail-closed 的 FAIL。回滾只需回退程式與文件 commit。

## Open Questions

無；issue #252 已界定必要分類、文件位置與敏感資訊邊界。
