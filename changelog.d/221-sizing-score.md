### Added

- **Issue #221：五維 sizing 評分（三維機械算＋二維宣告）**：`planning.py` 新增 `compute_sizing_score()`／`SizingScore`，純函式計算 acceptance_surfaces／spec_stability／orchestration，並讀取 plan frontmatter 宣告的 `domain_breadth`／`state_consistency`；`deck/schema.py`／`deck/compile.py` 同步落地 gate_spine 兩層制（`band_triggered` 加掛層，預設 Yellow 起掛，band 未知時保守全含），`feature-oneshot` combo 的 `adversarial-review` 移入加掛層。
