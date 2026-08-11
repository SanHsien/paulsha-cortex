**Issue #456：定案候選 (executor, model_id, persona) 身分矩陣**：新增
`docs/superpowers/specs/model-persona-roster-matrix.md`，以 launcher 硬約束（copilot 無
enforced read-only planning mode → planner／reviewer 兩格排除；agy 唯一 invocation 為
headless plan+sandbox 且 `commit_required` 不 plumb → builder 排除；cg zero-tool 建構期
raise → builder 排除）先於 benchmark 排除 4 格，定案 5 身分登錄 roster（`agy/gemini-3.1-pro-high`、
`copilot/gpt-5.4`、`claude/sonnet`、`codex/gpt-5.3-codex-spark`、`cg/glm-5.2`，model_id 皆
repo 內有據可查；`gemini-3.6-flash-high`／`gpt-5.4-codex` 列待確認不登錄）、
`independence_domain` 依模型血統填法（cg → `zhipu`）與 builder/reviewer 分離相容性檢核、
「registry 登錄 ≠ 本機可用」的三 seam 分離機制（live_probe／runtime preflight／
`provider:executor` 閘門，與 #442 解耦），並算出「待 benchmark」格數 **N = 11**（現階段
pilot-v1 可實測 3 格 builder 維度）供 #455 消費。roster 已以 `IdentityRegistry.from_rows`
實測通過既有 fail-closed 驗證（正向載入＋agy planning 綁定／重複身分兩條負向）。docs-only，
不改 registry 檔案與任何 `.py`。
