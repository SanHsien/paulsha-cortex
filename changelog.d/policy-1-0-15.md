### Changed

- **同步 paulsha-conventions 1.0.14 → 1.0.15**：`.project-policy.yml` 與 `CLAUDE.md`（`managed-by`／`policy_version`／profile 段）皆 bump 至 `1.0.15`；`Policy Check` workflow 的 `uses:` 與 `policy_engine_ref` 重新雙重釘選至 `hamanpaul/paulsha-conventions@a764806046c410eb4f254ac0b6a8aec8b7559dab`（= engine tag `v1.0.15`，尾註供 R-23 對齊）；`README.md` 開發備註的引擎版號字樣同步更新。1.0.14→1.0.15 未新增規則編號，僅新增 tag 觸發的 runtime bundle release workflow，故 `CLAUDE.md` 不需新增規則段落。
