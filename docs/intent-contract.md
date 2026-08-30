# Cortex Intent Contract v1

`intent.md` 是進入 Cortex 工作生命週期之前的人類意圖文件。它回答「要解決什麼、
為什麼、受哪些限制」，但不是完整 spec、plan，也不構成派工授權。

本契約受 Anthropic 官方 [AI-Native SDLC Playbook 的 intent capture](https://academy.claude.com/courses/ai-native-sdlc-playbook/capture-intent)
啟發；`cortex-intent/v1` 是 Cortex 自己的治理契約，不宣稱為通用業界標準。

## 放置位置

一般情況下，intent 跟產品一起版本控制：

```text
<product-repo>/
└─ intent/
   └─ <work-id>/
      └─ intent.md
```

只有同一個 intent 明確跨越多個 repo 時，才使用專用 intent repo；每個受影響 repo
仍需保存可追溯的 work-item link。Cortex repo 保存契約與範例，不集中代管所有產品 intent。

## Frontmatter

每份 `cortex-intent/v1` 文件必須以 YAML frontmatter 宣告以下四個欄位：

```yaml
---
schema: cortex-intent/v1
work_item: sample-change
status: draft
owner: product-owner
---
```

- `schema`：固定為 `cortex-intent/v1`。
- `work_item`：穩定、repo-local 的小寫識別；只允許英數、`.`、`_`、`-`。
- `status`：只允許 `draft`、`accepted`、`rejected`。
- `owner`：負責接受或拒絕意圖的人類角色或可稽核身分。

`status: accepted` 只是文件內容，不是自我授權。任何 agent、hook 或 CLI 都不得只讀這個
欄位就 claim、start 或 dispatch。

## 必要章節

章節標題固定使用以下名稱，方便人類閱讀及後續確定性工具檢查：

1. `## Problem`
2. `## Proposed outcome`
3. `## Affected users and systems`
4. `## Constraints`
5. `## Out of scope`
6. `## Evidence and sources`
7. `## Open questions`
8. `## Success signals`

`Open questions` 可以保留未決項目；進入 spec/design 時，必須逐項解決，或明確帶入
後續 artifact。Intent gate 不應只因存在 open question 就拒絕草稿或接受決策。

## 人類決策證據

接受或拒絕 intent 的證據必須綁定不可混淆的版本，至少包含：

- intent 所在的 exact Git commit SHA；
- 決策 `accepted` 或 `rejected`；
- approver 身分與時間；
- 可重讀的 review、merge 或簽署決策 reference。

Git 作者、commit 歷史與檔案內的 `owner` 都不能單獨替代接受決策。Intent 在核准後若有
任何修改，原決策不再覆蓋新 SHA，必須重新審視。

## Cortex 生命週期對映

```text
idea / ticket / incident
          |
          v
intent/<work-id>/intent.md
  draft + 人類修正
          |
          v
accepted decision on exact SHA
          |
          v
topic / proposed evidence only
          |
          v
spec / design / plan / confirmed Todo
          |
          v
todo -> start -> WorkflowRun -> Candidate -> Verify -> Review -> Delivery
```

規則如下：

- `draft` 或 `rejected` intent 不改變 Cortex lifecycle state。
- `accepted` intent 最多提供 `topic`／proposed 階段的來源與追溯資訊。
- Intent 不是現行 `cortex work link --kind` 的 authority kind；v1 不新增 CLI intake 行為。
- 只有既有 confirmed Todo 來源（Todo、accepted spec/plan 或 active OpenSpec）才能讓 work
  item 進入 `todo` 並取得 `start` next action。
- 後續 spec、plan、acceptance criteria 應回指 intent 的 repo-relative path 與 exact SHA；
  不能只靠相似標題或 slug 推斷關聯。

## v1 非目標

- 不自動從自然語言生成 accepted intent。
- 不把產品決策交給結構驗證器。
- 不新增 daemon、service、model call 或自動 dispatch。
- 不讓 Cortex 取代產品 repo 作為需求內容的保存位置。

可直接複製的草稿見
[`examples/intent/sample-change/intent.md`](../examples/intent/sample-change/intent.md)。
