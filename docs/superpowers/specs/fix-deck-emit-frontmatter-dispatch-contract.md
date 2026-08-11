# Fix Deck Emit Frontmatter Auto Dispatch Contract

`cortex deck compile --emit` 產生的 spec 在 `dispatch: auto` 前，`target_branch` 與 `verification` 需補齊以下欄位，否則會被 manager 以 `dispatch: hold` + parse_error 停住（不會派工）。

## 檢核欄位

- `target_branch`：非空字串，通常為 `feature/<change>`（若無 change 則 fallback `feature/<slug>`，並發 warning）。
- `verification`：完整物件，必含以下欄位且符合 `paulsha_cortex.coordinator.verification.validate_verification_contract()`：
  - `docs_class`
  - `required_artifacts`
  - `checks`
  - `tests`
  - `full_suite`
- `executor` / `model_id`：optional，但必須成對宣告且皆為非空字串；宣告時 manager 會先用 `model-identities.yaml` 驗證該 `(executor, model_id)` 是否已註冊，未宣告時沿用 fanout/tick 的 builder 預設值。Deck compile 本身不會自動輸出這兩欄，需要 operator 在確定要逐 slice 覆寫時手動補上。

### `checks` 要求

- 至少一筆 `{"kind": "persona-scope"}`。
- `command` 型檢查至少一筆，且 `name` 必為 `"policy"`（例如 policy check）。

### `full_suite` 要求

- 必有 `baseline: no-regression`。

## 建議樣板（emit 時可直接對齊）

`deck compile` 自 #380 起會從目標 repo 的 `.project-policy.yml`（`preflight.steps`，
typed：`kind: validation` / `kind: tests` + `argv` + `timeout_seconds`）自動導出下列
`checks[name=policy]` 與 `tests`/`full_suite` 的 `argv`／`timeout_seconds`；偵測不到對應
step 時（無 `.project-policy.yml`，或有檔但缺該 kind）會改填 fail-closed placeholder（誤
執行會非零退出）並在 compile 輸出印醒目 warning——這種情況務必在翻 `dispatch: auto`
前手動改成下方樣板等級的真實指令，不可原樣放行。

```yaml
target_branch: feature/101
verification:
  docs_class: code
  required_artifacts: []
  checks:
    - kind: persona-scope
    - kind: command
      name: policy
      argv: [python3, -m, policy_check, --repo, .]
      cwd: .
      timeout_seconds: 30
  tests:
    - argv: [python3, -m, pytest, tests/, -q]
      cwd: .
      timeout_seconds: 60
  full_suite:
    argv: [python3, -m, pytest, tests/, -q]
    cwd: .
    timeout_seconds: 60
    baseline: no-regression
```
