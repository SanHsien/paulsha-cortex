---
status: accepted
work_item: fix-handoff-manifest-reconcile
---

# fix-handoff-manifest-reconcile Todo

## Tasks

- [ ] run_tick 的 already_terminal 掃描改與 registry 對帳
- [ ] fanout lane 補同等過濾
- [ ] recovery 動作作廢或標記 superseded manifest
- [ ] 回歸測試：殘留 manifest 且 registry 已復原時 tick 不再略過
