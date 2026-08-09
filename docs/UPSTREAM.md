# Upstream tracking

最後檢查：2026-08-09

| 欄位 | 值 |
| --- | --- |
| fork | `SanHsien/paulsha-cortex` |
| upstream | `hamanpaul/paulsha-cortex` |
| upstream main | `b868760` |
| origin main | `c332e9d` |
| rev-list `origin/main...upstream/main` | fork ahead 2 / behind 0 |
| 本輪決策 | 無待 port upstream commit；建立 Windows-first feature branch |

## 同步規則

```powershell
git fetch upstream main --tags --prune
git rev-list --left-right --count origin/main...upstream/main
git log --oneline origin/main..upstream/main
```

逐筆記錄 upstream commit 的採用、部分採用、延後或不採用理由。不要在有 fork-specific Windows adapters 時做無審查的整批 merge。同步後必須跑原生 Windows full gate，Linux CI 則守住 systemd/Bash/sandbox 相容面。
