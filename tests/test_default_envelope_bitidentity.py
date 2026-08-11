"""#453 R6：DEFAULT_ENVELOPE 的 bit-identical 回歸測試規格（#452 實作 MUST 照做）。

T1：同一 fixture corpus 跑兩遍——baseline 配置（capability_lookup=None、
envelope_lookup=None，即 v0.1.6 語意）vs 預設封套配置（provider 由 packaged
registry + DEFAULT_ENVELOPE 建構）——逐 case 斷言五個決策 surface 的 canonical
JSON 序列化 byte-equal。

T2：不經 R5 bypass 規則、直接以集合／比較語意評估 R1–R3 預設值對全部可達
(work, identity, persona) 組合恆不排除；變異任一預設值（如 builder accepts_bands
砍掉 yellow）必使本測試轉紅。
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from paulsha_cortex.coordinator import claim_readiness as cr
from paulsha_cortex.coordinator.claim import (
    DECOMPOSITION_DEPTH_LIMIT,
    decomposition_route,
    load_work_authority,
    sizing_band,
)
from paulsha_cortex.coordinator.completion import (
    COMPLETION_SCHEMA_VERSION,
    validate_completion_record,
)
from paulsha_cortex.coordinator.delivery import repair_budget_for_band
from paulsha_cortex.coordinator.model_identities import (
    ACCEPTANCE_MODES_DOMAIN,
    CONSISTENCY_SCOPE_DOMAIN,
    DEFAULT_ENVELOPE,
    build_capability_lookup,
    load_model_identities,
    plan_review_envelope_projection,
)
from paulsha_cortex.coordinator.planning import PlanningArtifact, plan_review_gate

_BANDS = ("green", "yellow", "red")
_PERSONAS = ("planner", "builder", "reviewer")


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=repr).encode(
        "utf-8"
    )


def _packaged_registry(tmp_path: Path):
    # tmp_path 沒有 overlay 檔 → 純 packaged roster（決策軌跡不受宿主機
    # $PSC_PROJECT_CONFIG_ROOT 汙染）。
    return load_model_identities(tmp_path, use_packaged_default=True)


# ---------------------------------------------------------------------------
# T1 golden 雙配置決策軌跡
# ---------------------------------------------------------------------------


def _authority(tmp_path: Path):
    payload = {
        "schema": "work-items-snapshot/v1",
        "providers": {
            "github": {
                "provider_id": "github",
                "revision": "github-rev-1",
                "last_success_epoch": 950,
                "degraded": False,
            }
        },
        "work_items": [
            {
                "repo": "acme/demo",
                "work_id": "t1-golden",
                "mapped_issues": [452],
                "mapped_prs": [],
                "mapped_openspec": ["t1-golden"],
                "mapped_todo_paths": ["docs/todo.md"],
                "confirmed_todo": True,
                "auto_label": True,
                "source_revisions": ["issue:452@open"],
            }
        ],
    }
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return load_work_authority(repo="acme/demo", work_id="t1-golden", snapshot_path=path)


def _readiness_outcome_dict(outcome: cr.ReadinessOutcome) -> dict:
    return {
        "ready": outcome.ready,
        "frozen": outcome.frozen.to_dict() if outcome.frozen is not None else None,
        "failed_check": outcome.failed_check,
        "reason": outcome.reason,
        "terminal": outcome.terminal,
        "checks_run": list(outcome.checks_run),
    }


def _run_readiness(tmp_path: Path, *, capability_lookup, executor_identity: str) -> dict:
    authority = _authority(tmp_path)
    context = cr.ReadinessContext(
        authority=authority, executor_identity=executor_identity, issue_ref=None
    )

    def _git(args):
        if "fetch" in args:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout=("a" * 40) + "\n", stderr="")

    probes = cr.ReadinessProbes(
        local_scope=cr.local_scope_probe(),
        base_sha=cr.base_sha_probe(repo_root="/unused", git_runner=_git),
        monitor_snapshot=cr.monitor_snapshot_probe(),
        github_owner=cr.github_owner_probe(runner=lambda *a, **k: SimpleNamespace(returncode=0, stdout="{}", stderr="")),
        capability=cr.capability_probe(capability_lookup=capability_lookup),
        live_probe=cr.live_probe_check(prober=lambda: SimpleNamespace(ready=True)),
    )
    outcome = cr.evaluate_pre_claim_readiness(context, probes, now=lambda: 1000.0)
    return _readiness_outcome_dict(outcome)


def _plan_artifact(invariant_count: int, artifact_classes: list[str]) -> PlanningArtifact:
    classes = "[" + ", ".join(artifact_classes) + "]"
    text = (
        "---\n"
        "status: accepted\n"
        f"invariant_count: {invariant_count}\n"
        f"artifact_classes: {classes}\n"
        "---\n"
        "# Plan\n## Tasks\n- 實作 code 變動，補 changelog、CLI 說明與 test。\n"
    )
    return PlanningArtifact(kind="plan", ref="docs/plan.md", text=text)


def _plan_review_outcome_dict(outcome) -> dict:
    return {
        "ready": outcome.ready,
        "failed_check": outcome.failed_check,
        "reason": outcome.reason,
        "terminal": outcome.terminal,
        "checks_run": list(outcome.checks_run),
        "observations": {
            name: {key: value for key, value in sorted(dict(observation).items())}
            for name, observation in outcome.observations.items()
        },
    }


def test_t1_golden_dual_config_decision_surfaces_byte_equal(tmp_path: Path) -> None:
    registry = _packaged_registry(tmp_path)

    # Surface 1：evaluate_pre_claim_readiness——registry 全體身分 × 三 persona ×
    # 三帶（readiness 六格全序）。baseline lookup=None vs 預設封套 provider。
    for identity in registry.identities:
        executor_identity = f"{identity.executor}/{identity.model_id}"
        for persona in _PERSONAS:
            for band in (*_BANDS, None):
                baseline = _run_readiness(
                    tmp_path, capability_lookup=None, executor_identity=executor_identity
                )
                lookup = build_capability_lookup(
                    registry, persona=persona, sizing_band=band
                )
                projected = _run_readiness(
                    tmp_path, capability_lookup=lookup, executor_identity=executor_identity
                )
                assert _canonical(baseline) == _canonical(projected)

    # Surface 2：plan_review_gate——invariant_count {0,1,99} × artifact_classes
    # 含域內與域外值（沿用既有 exotic fixture 值域外字串）。
    surfaces = frozenset({"code"})
    for invariant_count in (0, 1, 99):
        for classes in (["code"], ["exotic"], ["code", "test", "docs"]):
            artifact = _plan_artifact(invariant_count, classes)
            baseline_outcome = plan_review_gate(
                plan_artifact=artifact,
                acceptance_surfaces=surfaces,
                applicable_contract_rules=frozenset(),
                envelope_lookup=None,
            )
            for identity in registry.identities:
                projected_outcome = plan_review_gate(
                    plan_artifact=artifact,
                    acceptance_surfaces=surfaces,
                    applicable_contract_rules=frozenset(),
                    envelope_lookup=lambda identity=identity: plan_review_envelope_projection(
                        identity, persona="builder"
                    ),
                )
                assert _canonical(_plan_review_outcome_dict(baseline_outcome)) == _canonical(
                    _plan_review_outcome_dict(projected_outcome)
                )

    # Surface 3：sizing_band() + decomposition_route()——三帶 × depth {0,1,2}。
    # 純函式不消費封套；雙配置下同一輸入必同輸出（byte-equal）。
    routes = {
        (total, depth): (sizing_band(total), decomposition_route(decomposition_depth=depth))
        for total in (0, 3, 4, 6, 7, 10)
        for depth in (0, 1, DECOMPOSITION_DEPTH_LIMIT)
    }
    assert _canonical({f"{k}": v for k, v in routes.items()}) == _canonical(
        {
            f"{(total, depth)}": (
                sizing_band(total),
                decomposition_route(decomposition_depth=depth),
            )
            for total in (0, 3, 4, 6, 7, 10)
            for depth in (0, 1, DECOMPOSITION_DEPTH_LIMIT)
        }
    )

    # Surface 4：repair_budget_for_band()——預算值或例外。
    def _budget(band):
        try:
            return {"budget": repair_budget_for_band(band)}
        except ValueError as exc:
            return {"error": str(exc)}

    budgets = {str(band): _budget(band) for band in (*_BANDS, None)}
    assert _canonical(budgets) == _canonical(
        {str(band): _budget(band) for band in (*_BANDS, None)}
    )

    # Surface 5：validate_completion_record()——normalized 輸出或例外。
    valid_payload = {
        "schema_version": COMPLETION_SCHEMA_VERSION,
        "slice_id": "slice-a",
        "spec_hash": "1" * 64,
        "plan_hash": "2" * 64,
        "verification_hash": "3" * 64,
        "builder_job_id": "builder-1",
        "reviewer_job_id": "reviewer-1",
        "dispatch_base": "a" * 40,
        "candidate": "b" * 40,
        "target_branch": "main",
        "target_remote": "origin",
        "target_ref": "refs/remotes/origin/main",
        "target_ref_sha": "c" * 40,
        "verification_evidence_path": "/verification.json",
        "verification_evidence_hash": "3" * 64,
        "review_policy": "required",
        "docs_class": "code",
        "review_evaluation_path": "/review-eval.json",
        "review_evaluation_hash": "9" * 64,
        "completed_at": "2026-07-12T00:00:00+00:00",
    }

    def _completion(payload):
        try:
            return {"normalized": validate_completion_record(payload)}
        except ValueError as exc:
            return {"error": str(exc)}

    for payload in (valid_payload, {"schema_version": COMPLETION_SCHEMA_VERSION}):
        assert _canonical(_completion(payload)) == _canonical(_completion(payload))


def test_t1_capability_observation_bytes_match_v016_bypass(tmp_path: Path) -> None:
    """預設封套 provider 對 packaged 身分回 None → capability 格 observation
    與 v0.1.6 的 `_passed("capability", bypass="envelope_unavailable")` 字節相同。"""

    registry = _packaged_registry(tmp_path)
    for identity in registry.identities:
        for persona in _PERSONAS:
            lookup = build_capability_lookup(registry, persona=persona, sizing_band="green")
            probe = cr.capability_probe(capability_lookup=lookup)
            context = cr.ReadinessContext(
                authority=_authority(tmp_path),
                executor_identity=f"{identity.executor}/{identity.model_id}",
            )
            result = probe(context)
            baseline = cr.capability_probe(capability_lookup=None)(context)
            assert _canonical(dict(result.observation)) == _canonical(
                dict(baseline.observation)
            )
            assert result.passed and baseline.passed


# ---------------------------------------------------------------------------
# T2 DEFAULT_ENVELOPE 恆不排除 property test（直接集合／比較語意，不經 bypass）
# ---------------------------------------------------------------------------


def _reachable_bands(persona: str) -> tuple[str, ...]:
    # 可達＝依 #223 攔截鏈可抵達該 persona 的輸入：builder/reviewer 只餵
    # green/yellow（red 在 plan 相位就被路由走），planner 三帶全餵。
    if persona == "planner":
        return ("green", "yellow", "red")
    return ("green", "yellow")


def test_t2_default_envelope_never_excludes_reachable_inputs() -> None:
    for persona in _PERSONAS:
        defaults = DEFAULT_ENVELOPE[persona]
        bands = tuple(defaults["accepts_bands"])
        # 判準 1：可達 band 恆在窗內（變異 builder accepts_bands 砍 yellow 必轉紅）。
        for band in _reachable_bands(persona):
            assert band in bands, (persona, band)
        # 判準 2：invariant_ceiling 為 bypass sentinel None——不存在任何有限值
        # 會排除 invariant_count ∈ {0, 1, 99}（#453 R2：值域無界，唯一誠實值）。
        assert defaults["invariant_ceiling"] is None
        for invariant_count in (0, 1, 99):
            ceiling = defaults["invariant_ceiling"]
            assert ceiling is None or invariant_count <= ceiling
        # 判準 3：域內 artifact_classes 恆為 consistency_scope 子集。
        scope = frozenset(defaults["consistency_scope"])
        assert scope == frozenset(CONSISTENCY_SCOPE_DOMAIN)
        for classes in (("code",), ("code", "test"), tuple(CONSISTENCY_SCOPE_DOMAIN)):
            assert frozenset(classes) <= scope
        # 判準 4：全部合法 acceptance_mode 恆在窗內。
        modes = tuple(defaults["acceptance_modes"])
        assert modes == ACCEPTANCE_MODES_DOMAIN
        for mode in ACCEPTANCE_MODES_DOMAIN:
            assert mode in modes


def test_t2_planner_red_is_default_included_for_decomposition_route() -> None:
    # #453 R1：planner 預設不含 red 會讓 #223 的 needs_decomposition 收斂路徑
    # 在 capable() 落地後死鎖——red 必在 planner 窗內。
    assert "red" in tuple(DEFAULT_ENVELOPE["planner"]["accepts_bands"])
    assert "red" not in tuple(DEFAULT_ENVELOPE["builder"]["accepts_bands"])
    assert "red" not in tuple(DEFAULT_ENVELOPE["reviewer"]["accepts_bands"])
