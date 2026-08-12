# profile-lane-patchmud-drift

- **Issue #466：profile 巷道對 patchmud main（PR #15 後）的 drift 修正**
  （`paulsha_cortex/coordinator/model_profile.py`）：
  - **A-1 report 聚合鍵改從 report 本身取**：patchmud PR #15 起 `run.yaml` 記
    `normalize_model_spec()` 展開後的完整 model spec（非 CLI 別名，且
    anthropic↔claude CLI fallback 隨憑證狀態浮動），舊實作以別名查
    `clear_rate` 榜必落 `identity-not-in-report`、巷道永遠產不出實測封套。
    新增 `_report_group_key()`：profile 的 runs_root 為單一身分專用，report 內
    必恰一組 `(model, loadout)`，多組即 `report-group-ambiguous` fail-closed。
  - **A-2 adapter 別名表更新**：patchmud 已落地 codex／agy OAuth headless
    adapter（paulsha-patchmud#14），「僅 anthropic adapter」的誠實約束註解過時；
    補 `("agy", "gemini-3.1-pro-high") → "agy:gemini-3.1-pro"` 對應（完整 spec、
    不用短別名），明寫 CLI adapter effort 硬編 `high` 的對應限制；codex 身分
    待 #456 R4 登錄後補格。
  - **A-3 deck 指紋改聚合 encounter provenance pin**：原 rglob 全檔 hash 會把
    `patchmud validate-deck` 對 `reference_timings` 的例行覆寫誤判成 deck 變更、
    誤觸全量重評；改為聚合各 encounter `provenance.yaml` 的 `content_sha256`
    （與 patchmud `encounter_content_sha256` pin 同語意，#452 D 票面原意），
    provenance 缺漏 fail-closed。
  - **A-4 run 封存耐久化**：runs_root 從 `mkdtemp` 改落 patchmud repo
    `runs/profile-<executor>-<model_id>-<stamp>/`（比照 #455 實測慣例，不進
    版控），registry 的 `profile_provenance.observation.runs_root` 記出處——
    落進 registry 的封套值可回溯到 events／ledger／replay 證據。
- **spec 勘誤追記**（`envelope-mapping-spec.md`、`benchmark-cost-baseline.md`）：
  paulsha-patchmud#21 證實「haiku 4/8」與「同母題變體 clear 分歧」兩個定案錨點
  實為 unified diff 協定噪音（非能力／變體訊號）；定案方向不變，但 R3 人工閘
  追記「pilot-v1 來源的降級提案 MUST 先以 `end_reason`／`protocol_failed`
  排除協定噪音」（paulsha-patchmud#24 落地後可直接讀 report `runs[]`）。
