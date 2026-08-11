# envelope-mapping

- **Issue #454（#452 子項）：patchmud ranked 榜 → 封套四欄位的映射純函式與門檻定案**：
  新增 `paulsha_cortex/coordinator/envelope_mapping.py`（`map_report_to_envelope()`，
  純函式、無 I/O、禁止 import patchmud）與 `tests/test_envelope_mapping.py`
  （34 案：重跑 bit-identical、門檻邊界含非二進位分母整數算術、default 回退理由碼、
  fail-closed 驗證、planner red 釘入、DEFAULT_ENVELOPE 常數守值）。
- 新增 `docs/superpowers/specs/envelope-mapping-spec.md`，票面四待決全數定案：
  (1) v1 只落 `accepts_bands`，其餘三欄誠實維持 `#453` 預設並逐欄留
  `not-measurable:*` 理由碼；(2) 門檻定 `clear-rate-ladder-v1`——固定門檻
  （否決 report 內相對排名：單格 report 退化、違反 #455 §4.1 指紋語意）、
  整數交叉相乘比較，`clear_rate ≥ 3/4 → [green, yellow]`、`≥ 1/4 → [green]`、
  低於地板 → 空集且 `registry_writable: false`；未標註 band 的 deck 走此階梯，
  將來 card 標註後 per-band clear-rate（`banded-clear-rate-v1`）整體取代、
  前置為上游 report 增列 per-run encounter id；planner 的 red 依 #223 收斂路徑
  結構性釘入、不受門檻管轄；(3) 人工複核閘要——函式只產 diff 預覽 payload，
  registry 寫入經 #452 CLI 人工確認，不自動落地；(4) 映射歸屬 cortex 側，
  patchmud 維持零 cortex 依賴。另定混合 provenance 的 seam 投影規則（所需欄位
  任一 default → 維持 bypass 字節；v1 決策下 envelope_lookup 投影恆 None，
  行為變更被精確限制在 capability band 判準一條通道）。
