### Fixed

- **Issue #220：final attestation 必須先於 merge mutation**：`github_delivery.py` 的 `GitHubDeliveryClient.merge_if_ready()` 拆成兩段——`evaluate_final_gate()` 只重讀 remote facts 並評估閘門，回傳可持久化的 `FinalGateVerdict`（綁定 repo／PR／candidate head／authority digest）；`commit_merge()` 要求傳入該 verdict，且 repo／PR／candidate／authority digest 須與呼叫當下完全相符，否則 fail closed，從不下 merge 指令。`delivery.py` 的 `ShipOrchestrator.merge_if_ready()` 改為先呼叫 `evaluate_final_gate()` 取得 verdict、綁定 `work_authority_digest(authority)`，才呼叫 `commit_merge()`，結構性堵住「先 merge 再補 attestation」的倒置情形（hippo #18 實案）。`merge_if_ready()` 維持既有相容行為。
