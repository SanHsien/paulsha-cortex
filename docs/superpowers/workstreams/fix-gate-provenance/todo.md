---
status: accepted
work_item: fix-gate-provenance
---

# fix-gate-provenance Todo

## Tasks

- [ ] gate 清單來源由 spec/plan 導出，取代 PSC_GATE_CMD_* 全權
- [ ] 空 ledger 不再 vacuous pass（無 gate 宣告時 fail-closed 或明示 bypass）
- [ ] 驗收判準定義納入 pinned input，builder 改判準即 mismatch
- [ ] slice lane 接上自報 vs ledger 對照
