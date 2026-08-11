"""#454（`#452` 子項）：patchmud ranked 榜 → 封套四欄位的映射純函式。

輸入 patchmud ``report.yaml``（schema v1）解析後的 dict＋身分／deck 識別資訊，
輸出封套四欄位（`accepts_bands`／`invariant_ceiling`／`consistency_scope`／
`acceptance_modes`）與逐欄 provenance 標記。定案全文見
``docs/superpowers/specs/envelope-mapping-spec.md``；四個票面待決的結論：

1. v1 只落 `accepts_bands` 一欄，其餘三欄誠實維持 `default`（#453 定值）。
2. 分數 → band 門檻走固定門檻 ``clear-rate-ladder-v1``（整數交叉相乘，無浮點）。
3. 本函式只產 diff 預覽 payload，不寫 registry；落地過人工複核閘（#452 CLI）。
4. 映射歸屬 cortex 側；本模組 MUST NOT import patchmud（測試鎖定）。

純函式契約：無 I/O、不 mutate 輸入、同一份輸入重跑輸出完全一致
（canonical JSON 序列化 byte-equal）。輸入契約違反一律 fail-closed
raise :class:`EnvelopeMappingError`，比照 ``model_identities.IdentityRegistry``
的逐欄驗證慣例；「量不到」不是契約違反，回退 `default` 並在 provenance 註明理由。
"""

from __future__ import annotations

from typing import Mapping

from paulsha_cortex.deck.schema import BAND_LEVELS

# #452 schema v3 落地後，封套常數的單一真值搬移至 model_identities.py
# （#454 spec 非目標第三條）；本模組 re-export 既有名稱維持 API 相容。
from .model_identities import (
    ACCEPTANCE_MODES_DOMAIN,
    CONSISTENCY_SCOPE_DOMAIN,
    DEFAULT_ENVELOPE,
    ENVELOPE_FIELDS,
    ENVELOPE_SOURCE_DEFAULT as SOURCE_DEFAULT,
    ENVELOPE_SOURCE_MEASURED as SOURCE_MEASURED,
)
from .workflow import MODEL_CHAIN_PERSONAS

#: 本模組支援的 patchmud report schema 版本（report.yaml 頂層 ``schema_version``）。
REPORT_SCHEMA_VERSION_SUPPORTED = 1

#: band 門檻規則識別碼。門檻常數屬於規則的一部分：任何門檻調整 MUST 換新
#: rule id（例如 ``clear-rate-ladder-v2``），使 provenance 中的 rule id ＋同一份
#: report 恆可重現同一輸出（spec R2）。
BAND_RULE_ID = "clear-rate-ladder-v1"

# 門檻以整數比值對 (分子, 分母) 表示，比較一律走整數交叉相乘
# （``clears * 分母 >= runs * 分子``），杜絕浮點邊界誤差；推導見 spec R2。
_YELLOW_MIN_RATIO = (3, 4)  # clear_rate ≥ 3/4 → 收 yellow
_GREEN_MIN_RATIO = (1, 4)  # clear_rate ≥ 1/4 → 收 green

# 逐欄 provenance 理由碼（穩定字串，供 #452 CLI diff 預覽與測試斷言）。
REASON_MEASURED_CLEAR_RATE = f"measured:{BAND_RULE_ID}"
REASON_BELOW_GREEN_FLOOR = f"measured:{BAND_RULE_ID}:below-green-floor"
REASON_PERSONA_DIMENSION_UNMEASURED = "persona-dimension-unmeasured"
REASON_IDENTITY_NOT_IN_REPORT = "identity-not-in-report"
REASON_INCOMPLETE_DECK_SAMPLE = "incomplete-deck-sample"
REASON_NO_DIRECT_OBSERVABLE = "not-measurable:no-direct-observable"
REASON_NO_ARTIFACT_CLASS_ANNOTATION = (
    "not-measurable:deck-cards-lack-artifact-class-annotation"
)
REASON_FOCUSED_TESTS_ONLY = (
    "not-measurable:deck-acceptance-covers-focused-tests-only"
)


class EnvelopeMappingError(ValueError):
    """report／輸入契約違反時 fail-closed 拒絕映射（不產出半套結果）。"""


def _require_nonempty_str(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnvelopeMappingError(f"{field} 必須是非空字串：{value!r}")
    return value


def _require_count(value: object, field: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EnvelopeMappingError(f"{field} 必須是整數：{value!r}")
    if value < minimum:
        raise EnvelopeMappingError(f"{field} 必須 ≥ {minimum}：{value!r}")
    return value


def _validate_deck(deck: object) -> dict:
    if not isinstance(deck, Mapping):
        raise EnvelopeMappingError(f"deck 必須是 mapping：{type(deck).__name__}")
    deck_id = _require_nonempty_str(deck.get("deck_id"), "deck.deck_id")
    content_sha256 = _require_nonempty_str(
        deck.get("content_sha256"), "deck.content_sha256"
    )
    encounter_count = _require_count(
        deck.get("encounter_count"), "deck.encounter_count", minimum=1
    )
    measured = deck.get("measured_personas")
    if not isinstance(measured, (list, tuple)):
        raise EnvelopeMappingError(
            f"deck.measured_personas 必須是 list：{measured!r}"
        )
    for persona in measured:
        if persona not in MODEL_CHAIN_PERSONAS:
            raise EnvelopeMappingError(
                f"deck.measured_personas 含非法 persona：{persona!r}"
                f"（允許 {sorted(MODEL_CHAIN_PERSONAS)}）"
            )
    return {
        "deck_id": deck_id,
        "content_sha256": content_sha256,
        "encounter_count": encounter_count,
        "measured_personas": tuple(measured),
    }


def _clear_rate_rows(report: Mapping[str, object]) -> list[Mapping[str, object]]:
    leaderboards = report.get("leaderboards")
    if not isinstance(leaderboards, Mapping):
        raise EnvelopeMappingError("report 缺 leaderboards mapping")
    board = leaderboards.get("clear_rate")
    if not isinstance(board, Mapping):
        raise EnvelopeMappingError("report 缺 leaderboards.clear_rate 榜")
    status = board.get("status")
    if status != "ok":
        raise EnvelopeMappingError(
            f"clear_rate 榜 status 非 ok：{status!r}（fail-closed，不以殘缺榜映射）"
        )
    rows = board.get("rows")
    if not isinstance(rows, list):
        raise EnvelopeMappingError("clear_rate 榜缺 rows list")
    for row in rows:
        if not isinstance(row, Mapping):
            raise EnvelopeMappingError(f"clear_rate row 必須是 mapping：{row!r}")
    return rows


def _find_group_row(
    rows: list[Mapping[str, object]], model: str, loadout: str
) -> Mapping[str, object] | None:
    matches = [
        row
        for row in rows
        if row.get("model") == model and row.get("loadout") == loadout
    ]
    if not matches:
        return None
    if len(matches) > 1:
        # (model, loadout) 是 report 的聚合鍵，重複列＝report 損毀，fail-closed。
        raise EnvelopeMappingError(
            f"clear_rate 榜對聚合鍵 ({model!r}, {loadout!r}) 出現 {len(matches)} 列"
        )
    return matches[0]


def _meets(clears: int, runs: int, ratio: tuple[int, int]) -> bool:
    numerator, denominator = ratio
    return clears * denominator >= runs * numerator


def _ladder_bands(clears: int, runs: int, persona: str) -> tuple[list[str], bool]:
    """clear-rate-ladder-v1：回傳 (bands, red_pinned)。

    未標註 sizing band 的 deck 只推得出 green/yellow 的分界（spec R2）；red
    永不由本規則授予。persona=planner 且階梯結果非空時，red 依 #223 收斂路徑
    （needs_decomposition 回派 planner 拆分）結構性釘入——red 對 planner 是
    路由必需、不是能力實測值，不受門檻管轄。
    """
    green, yellow = BAND_LEVELS[0], BAND_LEVELS[1]
    if _meets(clears, runs, _YELLOW_MIN_RATIO):
        bands = [green, yellow]
    elif _meets(clears, runs, _GREEN_MIN_RATIO):
        bands = [green]
    else:
        bands = []
    red_pinned = persona == "planner" and bool(bands)
    if red_pinned:
        bands.append(BAND_LEVELS[2])
    return bands, red_pinned


def _static_default_reasons() -> dict:
    """v1 恆為 default 三欄的理由（issue #454 表列的量測缺口，逐欄可追）。"""
    return {
        "invariant_ceiling": REASON_NO_DIRECT_OBSERVABLE,
        "consistency_scope": REASON_NO_ARTIFACT_CLASS_ANNOTATION,
        "acceptance_modes": REASON_FOCUSED_TESTS_ONLY,
    }


def _default_envelope_values(persona: str) -> dict:
    defaults = DEFAULT_ENVELOPE[persona]
    return {
        "accepts_bands": list(defaults["accepts_bands"]),
        "invariant_ceiling": defaults["invariant_ceiling"],
        "consistency_scope": list(defaults["consistency_scope"]),
        "acceptance_modes": list(defaults["acceptance_modes"]),
    }


def _result(
    *,
    fingerprint: dict,
    envelope: dict,
    source: dict,
    reasons: dict,
    observation: dict,
    registry_writable: bool,
) -> dict:
    return {
        "envelope": envelope,
        "provenance": {
            "fingerprint": fingerprint,
            "source": source,
            "reasons": reasons,
            "observation": observation,
            "registry_writable": registry_writable,
        },
    }


def _all_default_result(
    *, fingerprint: dict, persona: str, reason: str, observation: dict
) -> dict:
    reasons = {"accepts_bands": reason, **_static_default_reasons()}
    return _result(
        fingerprint=fingerprint,
        envelope=_default_envelope_values(persona),
        source={field: SOURCE_DEFAULT for field in ENVELOPE_FIELDS},
        reasons=reasons,
        observation=observation,
        # 全 default 沒有可落 registry 的實測值（#453 R4：registry 檔案永不
        # 寫入預設值），落地端見 False 即知本結果只是「維持現狀」的證明。
        registry_writable=False,
    )


def map_report_to_envelope(
    report: Mapping[str, object],
    *,
    executor: str,
    model_id: str,
    persona: str,
    deck: Mapping[str, object],
    patchmud_version: str,
    report_model: str,
    report_loadout: str,
) -> dict:
    """patchmud report dict → 封套四欄位＋逐欄 provenance（純函式）。

    參數：
      report: ``report.yaml``（schema v1）解析後的 dict；本函式只消費頂層
        ``schema_version`` 與 ``leaderboards.clear_rate.rows``（``runs``／
        ``clears`` 整數對，不用浮點 ``value``）。
      executor / model_id / persona: cortex 側身分三元（persona 必屬
        ``workflow.MODEL_CHAIN_PERSONAS``）。
      deck: deck 識別資訊 dict——``deck_id``／``content_sha256``／
        ``encounter_count``（全跑判準，#455 §4.3：不抽樣）／
        ``measured_personas``（該 deck 實際量測的 persona 維度；pilot-v1 為
        ``["builder"]``）。
      patchmud_version: 產出該 report 的 patchmud 版本（評測指紋成分）。
      report_model / report_loadout: 該身分在 report 聚合鍵 (model, loadout)
        中對應的鍵值（由呼叫端提供，本函式不猜測對應關係）。

    回傳 ``{"envelope": {...四欄...}, "provenance": {...}}``；provenance 含
    `#455` §4.1 定案的六元評測指紋（executor, model_id, persona, deck_id,
    deck_content_sha256, patchmud_version——**不含** pricing）、逐欄
    source（``measured``／``default``）與理由碼、觀測輸入、
    ``registry_writable``（False 時 #452 CLI MUST NOT 寫 registry）。
    """
    if not isinstance(report, Mapping):
        raise EnvelopeMappingError(
            f"report 必須是 mapping：{type(report).__name__}"
        )
    schema_version = report.get("schema_version")
    if schema_version != REPORT_SCHEMA_VERSION_SUPPORTED:
        raise EnvelopeMappingError(
            "report schema_version 不支援："
            f"{schema_version!r}（僅支援 {REPORT_SCHEMA_VERSION_SUPPORTED}）"
        )
    executor = _require_nonempty_str(executor, "executor")
    model_id = _require_nonempty_str(model_id, "model_id")
    patchmud_version = _require_nonempty_str(patchmud_version, "patchmud_version")
    report_model = _require_nonempty_str(report_model, "report_model")
    report_loadout = _require_nonempty_str(report_loadout, "report_loadout")
    if persona not in MODEL_CHAIN_PERSONAS:
        raise EnvelopeMappingError(
            f"persona 非法：{persona!r}（允許 {sorted(MODEL_CHAIN_PERSONAS)}）"
        )
    deck_info = _validate_deck(deck)

    fingerprint = {
        "executor": executor,
        "model_id": model_id,
        "persona": persona,
        "deck_id": deck_info["deck_id"],
        "deck_content_sha256": deck_info["content_sha256"],
        "patchmud_version": patchmud_version,
    }
    observation: dict = {
        "report_schema_version": schema_version,
        "model": report_model,
        "loadout": report_loadout,
    }

    rows = _clear_rate_rows(report)

    if persona not in deck_info["measured_personas"]:
        return _all_default_result(
            fingerprint=fingerprint,
            persona=persona,
            reason=REASON_PERSONA_DIMENSION_UNMEASURED,
            observation=observation,
        )

    row = _find_group_row(rows, report_model, report_loadout)
    if row is None:
        return _all_default_result(
            fingerprint=fingerprint,
            persona=persona,
            reason=REASON_IDENTITY_NOT_IN_REPORT,
            observation=observation,
        )

    runs = _require_count(row.get("runs"), "clear_rate row runs", minimum=1)
    clears = _require_count(row.get("clears"), "clear_rate row clears", minimum=0)
    if clears > runs:
        raise EnvelopeMappingError(
            f"clear_rate row clears > runs：{clears} > {runs}"
        )
    observation = {**observation, "runs": runs, "clears": clears}

    if runs < deck_info["encounter_count"]:
        # #455 §4.3 定案 8 關全跑不抽樣；不足全 deck 的樣本不得產出實測封套。
        # 註：report schema v1 的 run 列無 encounter 欄位，全覆蓋無法從
        # report 本身驗證，本判準是必要非充分條件（spec R2 記載上游缺口）。
        return _all_default_result(
            fingerprint=fingerprint,
            persona=persona,
            reason=REASON_INCOMPLETE_DECK_SAMPLE,
            observation=observation,
        )

    bands, red_pinned = _ladder_bands(clears, runs, persona)
    observation = {
        **observation,
        "band_rule": BAND_RULE_ID,
        "red_pinned": red_pinned,
    }

    envelope = _default_envelope_values(persona)
    envelope["accepts_bands"] = bands
    source = {field: SOURCE_DEFAULT for field in ENVELOPE_FIELDS}
    source["accepts_bands"] = SOURCE_MEASURED
    reasons = {
        "accepts_bands": (
            REASON_MEASURED_CLEAR_RATE if bands else REASON_BELOW_GREEN_FLOOR
        ),
        **_static_default_reasons(),
    }
    return _result(
        fingerprint=fingerprint,
        envelope=envelope,
        source=source,
        reasons=reasons,
        observation=observation,
        # 空的實測 accepts_bands 違反 #209 R2「非空」契約，不得落 registry；
        # 該身分該 persona 的處置（除名或明示維持 default）交人工複核閘。
        registry_writable=bool(bands),
    )
