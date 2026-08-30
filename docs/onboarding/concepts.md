# Concepts

這份文件只整理上手階段一定會碰到的四個名詞，定義直接沿用 UX 規格 §9，不額外發明新詞。

## 引用來源

- `docs/superpowers/specs/2026-07-21-porcelain-cli-ux-design.md` §9
- `docs/superpowers/specs/onboarding-docs-spec.md`
- issue #94

## 四個核心名詞

`spec`
: deck 產出的派工單，frontmatter 控制 `dispatch: hold` 或 `dispatch: auto`。

`job`
: 一次 executor 執行；例如 builder 或 reviewer 被派出去跑一次，就是一個 job。

`slice`
: 工作切片，包住 build、verification、review 等 gate 的單位。

`work`
: 跨 PR / issue 的統一生命週期 read model，給人類與 monitor 看整體工作狀態。

## 進入 runtime 之前：intent

`intent.md` 是 repo-local 的 proto-spec，記錄問題、預期結果、受影響對象、限制與未決問題。
它不是第五個 runtime object，也不是派工單。人類接受 intent 後，仍需形成 confirmed
Todo、accepted spec/plan 或 active OpenSpec，work 才能從 `topic` 進入 `todo`。

```text
intent (project artifact; exact-SHA approval)
  -> spec / plan / confirmed Todo
  -> job -> slice -> work
```

格式、核准證據與 fail-closed 邊界見 [Cortex Intent Contract v1](../intent-contract.md)。

## 一句話串起來

從使用者角度，可以把它看成：

`spec` -> `job` -> `slice` -> `work`

- 你先建立 `spec`
- manager 依 `spec` 派出 `job`
- 多個 `job` 與 gate 組成一個 `slice`
- monitor 再把跨來源事實投影成 `work`

## 誰負責寫入

- Manager daemon 是 workflow lifecycle 的唯一 writer
- Monitor 把多來源事實投影成 work read model

這也是為什麼日常 mutation 要走 `cortex run ...`、`cortex recover ...`、`cortex work ...` 之類的命令，而不是直接改內部狀態檔。

## 什麼時候需要知道這些

- Quickstart：知道 `dispatch: hold` 為什麼要改成 `dispatch: auto`
- 排錯：知道自己是在查 request、job、slice 還是 work
- 維運：知道 `cortex status` 與 `cortex list` 看的是不同層次
- Claim 一個 `work`：`cortex work intake`／`cortex work start` 要求 work item
  先進到 `todo` state 才會產生可 claim 的 `start` next_action；只 link 一個
  GitHub issue（`topic` state）並不夠。四態 read model 定義與 claim 前置
  條件見 `docs/unified-work-lifecycle.md`。
