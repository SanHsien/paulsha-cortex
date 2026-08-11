# patchmud-envelope-profile

- **Issue #452：patchmud 一次性評測產生模型能力封套，claim 時解析 planner／builder／reviewer；無 patchmud 走 bypass 預設**：
  - **A 評測巷道（選配、不在熱路徑）**：新增 `cortex model profile`
    （`paulsha_cortex/porcelain/model_profile.py`＋核心
    `paulsha_cortex/coordinator/model_profile.py`）——偵測不到 `patchmud`
    可執行檔即印明確 skip 訊息並 exit 0；對 packaged registry 內
    `source==default` 的身分逐 encounter 跑 deck（8 關全跑不抽樣、429 指數
    退避重試，#455 §4.2/§4.3）、收 report 餵 `map_report_to_envelope`、產
    unified diff 預覽，**經明確 `--apply` 才寫檔**（#454 R3 人工複核閘）；
    空 `accepts_bands`（below-green-floor）與 incomplete-deck-sample 絕不落
    registry。誠實約束：patchmud 僅 anthropic adapter，roster 內只有
    `claude/sonnet` 可被驅動，copilot／codex／agy／cg 逐格回報
    `adapter-unavailable` 維持 default。只經 CLI 邊界互動，cortex 不 import
    patchmud。
  - **B registry schema v2→v3**：`SUPPORTED_MODEL_IDENTITY_SCHEMAS` 加 3；
    `ModelIdentity` 新增封套四欄位＋`profile_provenance`（全選填、fail-closed
    值域驗證；「有寫必 measured、measured 必有寫」——registry 檔案永不寫入
    預設值，#453 R4）。`DEFAULT_ENVELOPE` 單一真值自 `envelope_mapping.py`
    整體搬移至 `model_identities.py`（#454 spec 非目標第三條），新增查表投影
    `project_envelope()`（缺省→套 `DEFAULT_ENVELOPE[persona]`、標
    `source=default`）。v1/v2 檔案照載、shadow 檢查語意不變。packaged registry
    升 v3 並登錄 #456 R3 的 5 身分 roster（純候選宣告、無實測封套；agy 列首
    位保住 planner 熱路徑選擇不變）。**部署遷移註記**：roster 由 1 身分擴為
    5 身分，若 host overlay（`$PSC_PROJECT_CONFIG_ROOT/model-identities.yaml`）
    已宣告被收編的四鍵之一（`copilot/gpt-5.4`、`claude/sonnet`、
    `codex/gpt-5.3-codex-spark`、`cg/glm-5.2`）且內容與 packaged 列不逐欄相等，
    升級後 registry 載入會 fail-closed（shadow 檢查語意本身不變，這是 roster
    擴張的側效應）——升級前請檢查各 host overlay，移除被收編的鍵或改成與
    packaged 逐欄相等；shadow 錯誤訊息已附行動指引。
  - **C claim 解析**：`MODEL_CHAIN_RESOLUTION_SOURCES` 擴充
    `patchmud-profile`／`default-envelope`（`registry` 保留為 legacy 值）；
    解析優先序 run-scoped override（#205）> measured 側寫 > registry/預設，
    `resolved_model_chain` durable evidence 記實際 source。提供
    `claim_readiness.capability_probe` 的 `capability_lookup` provider
    （`build_capability_lookup()`＋`evaluate_capability()`：#209 R1 六項全
    評估不短路、被排除原因可觀測；#453 R5 全 default → `None` 維持
    `envelope_unavailable` bypass 字節）——**claim 熱路徑尚未把 provider 傳入
    `capability_probe`，seam 接線待 #211 readiness pipeline 落地**；yellow plan
    review 的 `envelope_lookup` seam 則已實際接上
    （`manager._plan_review_envelope_lookup` →
    `plan_review_envelope_projection()`：#454 R5 兩鍵任一 default → `None`，
    v1 現況證據字節與 `envelope_lookup=None` 逐位元相同）。measured band 過濾
    與 measured-first 排序落在 `manager._workflow_identity_candidates`
    （override 不受過濾；primary_domain 偏好維持排序語意——preferred 排前、
    其餘候選保留在後，host overlay builder 不因 packaged 候選宣告被剔除，
    保住 #262 re-route fallback；部分剔除的排除理由落 manager log，全滅時
    fail-closed 錯誤訊息帶逐身分理由）。
  - **D 一次性語意**：評測指紋 `(executor, model_id, persona, deck_id,
    deck content_sha256, patchmud version)` 存 `profile_provenance.fingerprint`
    （不含 pricing，#455 §4.1）；指紋未變 → `already-profiled` skip、deck 內容
    pin 變更重評、`--force` 強制重評；熱路徑永不同步觸發評測。tick 補評測
    hook 本票評估後**不落地**（取捨：#454 R3 人工閘下 tick 只能產 proposal，
    而 manager tick 內 spawn 分鐘級 patchmud 子行程有 monitor 節拍風險），改
    以 `cortex inspect models` 顯示每身分封套值＋逐欄 source＋provenance 滿足
    可觀測性驗收。
  - **doctor 語意校正（#456 R6）**：packaged roster 使 claude review 身分
    「登錄即存在」，`review-sandbox` probe 改為僅在 host-local overlay 明示
    宣告 claude review 時維持 fail gate；候選宣告僅來自 packaged 時同樣檢查
    但降級 warn／非 required——登錄不隱含本機可用，roster 落地不得讓原本
    健康的部署 doctor 轉紅。
  - **測試**：`tests/test_default_envelope_bitidentity.py`（#453 R6 T1 golden
    雙配置五 surface canonical JSON byte-equal＋T2 預設值恆不排除 property）、
    `tests/test_model_identities_envelope_v3.py`（T3 loader 相容三件套＋#456
    R8 roster 正負向 fail-closed＋capability lookup seam）、
    `tests/test_model_profile_cli.py`（fake patchmud 執行檔 fixture，hermetic：
    skip／diff 預覽不寫檔／--apply round-trip／指紋 skip／--force／
    below-green-floor 不落檔／429 退避／inspect models 顯示）、
    `tests/test_model_chain_profile_resolution.py`（measured 優先序與 band
    過濾、override 優先、resolved source 三值、roster 前後 planner 選擇與
    secondary planner 不變、overlay builder 與 packaged roster 併存不被剔除）。
  - **對抗審查修正**：(1) builder primary_domain 偏好由「preferred 非空即整組
    收窄」改為「preferred 排前、其餘保留」——packaged 候選宣告不得把 host
    overlay 可跑 builder 擠出 #262 re-route fallback；(2) measured band 部分
    剔除（仍有存活候選）時排除理由落 manager log，不再靜默丟棄；(3)
    `IdentityRegistry.from_rows` 封套欄位閘門改由 schema_version 直接推導，
    建構層與檔案載入層同一條 v1/v2 fail-closed 規則；(4) `--identity` 過濾
    查無對應身分即明確報錯（exit 2；`/` 與 `:` 拼法皆接受），不再靜默產出
    零 cells；(5) T1 surface 3–5 改與 checked-in golden 比對（原自反相等為
    恆真式）、capability observation 補位測試 sizing_band 四值全掃；(6)
    shadow 錯誤訊息附「packaged roster v3 已收編此身分」行動指引。
