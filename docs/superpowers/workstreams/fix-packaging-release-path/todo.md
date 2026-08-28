---
status: accepted
work_item: fix-packaging-release-path
---

# fix-packaging-release-path Todo

## Tasks

- [ ] README 補 tag/wheel 安裝路徑與「git+main 為 mutable」告誡
- [ ] pyproject 定義 `[project.optional-dependencies].test`；tests.yml 移除 `|| true`
- [ ] smoke-install 加 Python 3.10–3.13 matrix；release.yml 補 tag vs VERSION 一致性檢查
- [ ] `requires-python` 收上界或補 classifiers
