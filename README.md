# paulsha-cortex

**Windows-first control plane for governed AI coding workflows.**

`paulsha-cortex` 把多 Agent 工程流程中最容易失真的部分集中成一個 vendor-neutral 控制面：從工作規格、派工、重試，到 deterministic verification、independent review、delivery 與 completion evidence，都由同一套 lifecycle authority 管理。

它不是聊天機器人，也不是另一個 IDE。Cortex 的角色是協調已安裝並登入的 headless executor（例如 `copilot`、`claude`、`codex`），並要求「完成」必須有可驗證的 Candidate、Verification、Review 與 Delivery 證據，而不是只相信 Agent 自報成功。

> **Fork status**
> `SanHsien/paulsha-cortex` 是 [`hamanpaul/paulsha-cortex`](https://github.com/hamanpaul/paulsha-cortex) 的 Windows-first development fork。它保留 Linux/systemd 相容性，但以原生 Windows 11 + PowerShell + Python 作為第一級開發與 CI 路徑。此 fork 用於研究、開發與驗證 agent engineering governance；目前不宣稱 production-ready。

## 為什麼會需要 Cortex？

當多個 coding agents、worktrees、reviewers 與 retry 同時存在時，最危險的不是「模型不會寫 code」，而是不同工具各自宣稱自己的局部狀態就是整體真相。Cortex 將這些狀態收斂成一條可驗證 lifecycle：

```text
intent (human-reviewed exact SHA; project artifact)
    ↓
spec / confirmed Todo authority
    ↓
plan → dispatch → candidate
                    ↓
             deterministic verify
                    ↓
             independent review
                    ↓
                 delivery
                    ↓
             completion record
```

核心原則：

- **單一 lifecycle authority**：`work / WorkflowRun / Job / Slice` 的狀態由 Cortex 管理；domain tools 只提供 artifacts。
- **意圖與派工權限分離**：`intent.md` 保存問題、目標與限制；只有 confirmed Todo/spec/plan authority 才能讓工作進入可 claim 狀態。
- **Executor-neutral**：builder / reviewer 可以來自不同 headless executors，不把 workflow 綁死在單一模型供應商。
- **Evidence before completion**：process exit code 0 不等於任務完成；verification、review 與 target-branch delivery 必須一致。
- **Fail-closed delivery**：authority、repo、Candidate、PR、checks 或 review evidence 無法證明一致時，不把工作投影為完成。
- **Operator-visible recovery**：`needs_human`、retry、request logs、inspect 與 doctor 都提供明確的 recovery 入口，不要求直接修改 runtime state files。

## SanHsien fork 的主要差異

相較 upstream，本 fork 專門把原生 Windows 路徑補成第一級能力：

- Windows 11 per-user Startup service backend，不要求管理員權限或 WSL。
- loopback TCP monitor transport，對應 Linux 的 Unix socket 路徑。
- Windows process wrapper、PID / file-lock / durability / path-safety 等平台可靠性修補。
- PowerShell bootstrap 與 canonical development gate。
- Windows-specific regression tests、GitHub Actions、CodeQL、dependency / upstream tracking。
- 持續保留 Linux/systemd 相容性；bubblewrap foreign-review sandbox 仍明確是 Linux-only。

詳細 fork 邊界、授權限制與 upstream 維護策略見 [docs/FORK.md](docs/FORK.md) 與 [docs/UPSTREAM.md](docs/UPSTREAM.md)。

## 平台支援

| 能力 | Windows 11 | Linux |
| --- | --- | --- |
| manager / monitor / workflow / review evidence | 原生支援 | 支援 |
| 背景 service | per-user Startup + PID/lock | systemd `--user` |
| monitor transport | loopback TCP endpoint manifest | Unix socket |
| 完整 pytest / build | Windows CI 權威 gate | Linux CI 相容 gate |
| bubblewrap foreign-review sandbox | 不支援、明確 skip | 支援 |

## Install

需求：Python 3.10–3.13、Git，以及至少一個已安裝並登入的 headless executor CLI。Windows-first 使用情境另建議 PowerShell 7。

評估用安裝：

```powershell
pipx install git+https://github.com/SanHsien/paulsha-cortex.git
cortex --help
cortex --version
```

正式驗收時不要把 mutable `main` 當固定依賴；請 pin 到已通過 fork CI 的 commit SHA：

```powershell
pipx install "git+https://github.com/SanHsien/paulsha-cortex.git@<commit-sha>"
```

也可以在 clone 後直接安裝：

```powershell
python -m pip install .
```

本 fork 目前不發布 wheel / sdist。upstream 根目錄尚無 LICENSE；GitHub fork 關係本身不等於取得一般性的再散布或改作授權。在 upstream 明確授權前，本 fork 不把衍生套件對外再發布。

## 新手上手

第一次接觸 Cortex，建議依序閱讀下列文件；這個區段是 onboarding 契約的穩定索引，README 本身不複製完整操作手冊：

1. [Quickstart](docs/onboarding/quickstart.md) — 從安裝、preflight、`cortex bootstrap` 到第一個 workflow。
2. [Concepts](docs/onboarding/concepts.md) — `spec`、`job`、`slice`、`work` 名詞與 lifecycle。
3. [Admin](docs/onboarding/admin.md) — `cortex service`、`cortex inspect`、`cortex request`、model profiling 與 digest delivery 日常維運。
4. [Runbook](docs/onboarding/runbook.md) — manager degraded、timeout、executor 與 recovery SOP。
5. [Troubleshooting](docs/onboarding/troubleshooting.md) — 常見故障快速對照。
6. [Upgrade](docs/onboarding/upgrade.md) — 升級與 pipx snapshot 更新。
7. [Rollback](docs/onboarding/rollback.md) — 回到上一個已知可用版本。

延伸閱讀：[Intent contract](docs/intent-contract.md)、[Development](docs/DEVELOPMENT.md)、[Unified Work Lifecycle](docs/unified-work-lifecycle.md)、[Monitor config](docs/monitor-config.md)、[Fork maintenance](docs/FORK.md)、[Upstream ledger](docs/UPSTREAM.md)、[Decisions](docs/DECISIONS.md)。

## Usage

### 最短上手路徑

先用 dry-run 確認環境，再 bootstrap Cortex：

```powershell
cortex bootstrap --dry-run
cortex bootstrap --instance cortex --repo-root (git rev-parse --show-toplevel)
```

建立第一個保持 `dispatch: hold` 的 sample workflow：

```powershell
cortex init-sample --task "example feature" --change example-feature
```

先檢查產出的 spec，將 glob plan 改成確切路徑，補齊 `target_branch` 與 `verification`；確認無誤後，**明確把 `dispatch: hold` 改成 `dispatch: auto`**。只有 `dispatch: auto` 且必要欄位完整的 slice 才會進入 ready set。

接著檢查 readiness 與 runtime：

```powershell
cortex ready --specs-dir "$HOME/.agents/specs"
cortex status
cortex inspect doctor --json
cortex service status --instance cortex --json
```

再明確指定 builder / reviewer 執行完整 tick：

```powershell
cortex tick `
  --specs-dir "$HOME/.agents/specs" `
  --executor codex `
  --model "<builder-model-id>" `
  --review-executor claude `
  --review-model "<reviewer-model-id>"
```

> `cortex status` 是 workflow / gate authority；`cortex service status` 只回答背景 service 是否存活。兩者不可互相替代。

### 日常操作

```powershell
cortex jobs
cortex stat "$JOB_ID"
cortex request list --json
cortex request show "$REQUEST_ID"
cortex request logs "$REQUEST_ID" --json
cortex inspect status --json
cortex inspect job "$JOB_ID"
cortex inspect work <work-id> --repo owner/repo
```

遇到 `needs_human` 時，先讀 `cortex status` 的 `attention[].next_actions`，再使用對應 operator action；不要直接修改 `jobs.json` 或其他 runtime authority files。

### 文件地圖

| 需求 | 文件 |
| --- | --- |
| 第一次建立 workflow | [Quickstart](docs/onboarding/quickstart.md) |
| 名詞：spec / job / slice / work | [Concepts](docs/onboarding/concepts.md) |
| intent 格式、人工核准與 authority 邊界 | [Intent contract](docs/intent-contract.md) |
| service / inspect / request / model profiling / digest delivery | [Admin](docs/onboarding/admin.md) |
| unified work read model、delivery closure、遷移 | [Unified Work Lifecycle](docs/unified-work-lifecycle.md) |
| monitor config precedence 與 ambient projects | [Monitor config](docs/monitor-config.md) |
| 常見事故與 recovery | [Runbook](docs/onboarding/runbook.md) |
| 升級 | [Upgrade](docs/onboarding/upgrade.md) |
| 回退 | [Rollback](docs/onboarding/rollback.md) |
| 疑難排解 | [Troubleshooting](docs/onboarding/troubleshooting.md) |
| Windows / Linux 開發 | [Development](docs/DEVELOPMENT.md) |
| fork 差異與採用限制 | [Fork maintenance](docs/FORK.md) |
| upstream 評估水位 | [Upstream ledger](docs/UPSTREAM.md) |
| 現行工程決策 | [Decisions](docs/DECISIONS.md) |

完整 lifecycle、delivery、model profiling、monitor、digest 與 migration 細節由上述 active 文件分工維護；README 不再作為第二份 admin / architecture manual。

## 安全與目前邊界

- 沒有 Web UI；工作意圖仍以 `intent.md`、spec、Markdown 與 structured files 為主。
- `cortex-intent/v1` 目前是 docs/schema-first contract，不新增 `kind=intent`、自動 claim 或 dispatch。
- verification 的 sanitized environment 不等於 network 或 filesystem sandbox。
- Windows 不提供 Linux bubblewrap foreign-review sandbox；此能力會明確 skip，不冒充已隔離。
- v1 自動 foreign review 仍受 tier / policy 邊界約束。
- executor 必須由使用者自行安裝、登入與管理憑證；Cortex 不代裝或代登入模型 CLI。
- 此 fork 追蹤快速變動的 upstream；production 採用前必須重新檢視 [docs/FORK.md](docs/FORK.md) 與 [docs/UPSTREAM.md](docs/UPSTREAM.md)，不能只以 CI 綠燈當成熟度證明。

## Development

Windows-first 開發入口：

```powershell
pwsh -File tools/bootstrap_dev.ps1
pwsh -File tools/dev_check.ps1 -Quick
```

完整測試：

```powershell
python -m pytest tests/ -q
```

CI 同時涵蓋 tests、persona scope、policy check、CodeQL，以及 dependency / upstream maintenance workflows。修改前請先閱讀 [CLAUDE.md](CLAUDE.md) 與 `.project-policy.yml`；本 repo 的 Markdown 也屬 policy `code_paths`，因此 PR 必須遵守 changelog fragment 與 policy gate。

## Version

目前 source version 的唯一權威是 [`VERSION`](VERSION)；不要在 README 另寫一份容易過期的版本號。tag / release 與 source version 的同步由 repo policy 與 release workflow 驗證。

本 fork 與 upstream 會持續分岔與選擇性同步。需要判斷「目前 fork 多了什麼、又落後 upstream 哪些內容」時，請看 [docs/FORK.md](docs/FORK.md)、[docs/UPSTREAM.md](docs/UPSTREAM.md) 與 GitHub compare，而不是從 README 的歷史快照推論。

## 相關工具

這四個 repo 各自治理 AI coding 的一層，可以單獨用，也可以疊起來用：

| 層 | Repo | 做什麼 |
| --- | --- | --- |
| 派工決策 | [agent-advisor](https://github.com/SanHsien/agent-advisor) | 風險分流路由 `solo`／`delegate`／`audit`／`full`：決定這件事要不要派工、派給誰 |
| 動作攔截 | [harness-guard](https://github.com/SanHsien/harness-guard) | agent runtime hook，在動手前後與收工時實際攔截危險指令、無證據宣稱、紅燈提交 |
| 產出品質 | [ai-quality-gates](https://github.com/SanHsien/ai-quality-gates) | 可執行規格與量化門檻：覆蓋率、突變測試、圈複雜度、依賴結構、有界 loop policy |
| 交付流程 | **paulsha-cortex（你在這裡）** | 多 Agent lifecycle：Candidate → Verify → Independent Review → Delivery → CompletionRecord |

相鄰但不同層：[opencodex](https://github.com/SanHsien/opencodex) 是供應商代理，決定這些 agent 背後能跑哪些 LLM，本身不約束 agent 行為。

## Provenance

Upstream：[`hamanpaul/paulsha-cortex`](https://github.com/hamanpaul/paulsha-cortex)。

本 repository 是維護型 Windows-first fork。上游治理模型與大量核心 runtime 仍屬 upstream 工作；本 fork 的公開價值在於 Windows 原生化、跨平台可靠性修補、Windows regression coverage，以及選擇性 upstream 維護，而不是重新宣稱 upstream 設計為自身原創。
