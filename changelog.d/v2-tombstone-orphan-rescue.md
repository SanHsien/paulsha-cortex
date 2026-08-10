### Changed
- **v2 墓碑錨點（issue 410 改名死結短期解）**：`fix-log-error-dedup-v2` 改名 v3 時仍有 ongoing run，形成「孤兒 run 不可 abandon（authority 隨改名消失）→ 其 issue 認領與 v3 相撞 → repo provider degraded → 全域凍結」三環死結。重加 v2 tombstone row（僅 path 錨點＋明示 exclude issue 374）恢復 authority 以 abandon 孤兒；abandon 後於收尾打掃移除。
