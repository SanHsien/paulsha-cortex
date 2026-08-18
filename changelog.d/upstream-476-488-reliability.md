# Upstream Issues 476–489 reliability batch

本批次採用並處理 upstream 仍 open 的 Issues 476–489，維持 fail-closed 與 exact-candidate 邊界：

- deployment：service install 在 enable 前建立或驗證 instance-local `project-cortex.yaml`。
- dispatch／recovery：builder prompt 帶 resolved worktree；pre-candidate recovery 同步移除 Git registry；`retry-build` 沿用正常 fanout 的 identity registry／launcher factory；舊 terminal attempts 僅保留為 audit evidence。
- reviewer：pre-launch absent artifact 以 request hash 分流；slice reviewer 強制 read-only，verdict 改由受控 terminal JSON 回收；Codex 固定相容 reasoning effort、接受唯一已知 stdin banner並要求 `turn.completed`；prompt enums 與 validator 共用常數。
- provider／operator：OAuth 訊號採 token boundary；status 以 bounded log tail、inactivity、runtime 與重複 tool-validation error 顯示 `stale-in-flight`，不自動終止工作。
- scope：`verification.allowed_paths` 可宣告 bounded repo-relative glob，與 persona `write_paths` 共同約束 Candidate；未宣告時 evidence 明示 `persona-only`。
- scope：`allowed_paths` 比對改為 path-aware，`*` 不再穿越 `/`，只有 `**` 跨層級；修正 slice scope 實際邊界比 spec 宣告的 bounded glob 更寬的缺口。

逐票決策、上游 commit／PR／issue 水位與不重複處理邊界記於 `docs/UPSTREAM.md`。
