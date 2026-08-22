### Changed
- Dependabot 的 `github-actions` 區塊新增 `codeql-action` 群組：`init` 與 `analyze` 必須跑同一個版本，拆成兩個 PR 各自升版會讓兩邊都紅（`Loaded a configuration file for version X, but running version Y`）。
