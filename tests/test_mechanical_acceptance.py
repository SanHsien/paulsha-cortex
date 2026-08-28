from __future__ import annotations

import json
from pathlib import Path
import pytest

from paulsha_cortex import cli as umbrella_cli
from paulsha_cortex.mechanical_acceptance import (
    AcceptanceReport,
    CheckResult,
    check_claim_vs_output,
    check_fact_freshness,
    check_internal_consistency,
    check_language_conventions,
    check_summary_vs_body,
    check_unsubstantiated_quantification,
    run_acceptance_checks,
)


class TestItem1ClaimVsOutput:
    def test_positive_claim_vs_output_matches(self) -> None:
        def verifier_rerun(params):
            return 0  # 0 residual findings

        res = check_claim_vs_output(
            claimed_count=0,
            claimed_fixed=True,
            claimed_params={"--pr-body": "Refs #292"},
            canonical_params={"--pr-body": "Refs #292"},
            rerun_fn=verifier_rerun,
        )
        assert res.passed is True
        assert res.exempted is False
        assert len(res.findings) == 0

    def test_negative_sample_277_residual_finding(self) -> None:
        """真實失敗樣本 #277：宣稱「Finding 1+2 已修」，但 Finding 2 只做了一半殘留。"""
        def verifier_rerun(params):
            return ["Finding 2 residual: monitor reader cannot readback status"]

        res = check_claim_vs_output(
            claimed_count=0,
            claimed_fixed=True,
            rerun_fn=verifier_rerun,
        )
        assert res.passed is False
        assert res.exempted is False
        assert len(res.findings) == 1
        assert "Finding 2 residual" in res.findings[0]

    def test_negative_sample_262_tampered_input_params(self) -> None:
        """真實失敗樣本 #262：subagent 自行將 brief 的 --pr-body Refs 改為 Fixes 以通過 gate。"""
        def verifier_rerun(params):
            # verifier 使用 canonical_params 重跑，發現並非 fail: 0
            if params.get("--pr-body") == "Refs #277":
                return 1  # 1 fail
            return 0

        res = check_claim_vs_output(
            claimed_params={"--pr-body": "Fixes #277"},
            canonical_params={"--pr-body": "Refs #277"},
            rerun_fn=verifier_rerun,
        )
        assert res.passed is False
        assert any("宣稱驗收參數與規範不符" in f for f in res.findings)
        assert any("殘留問題" in f for f in res.findings)

    def test_exemption_label(self) -> None:
        res = check_claim_vs_output(
            residual_findings=["residual bug"],
            pr_labels=["policy-exempt:claim-vs-output"],
        )
        assert res.passed is True
        assert res.exempted is True
        assert "policy-exempt:claim-vs-output" in res.exemption_reason


class TestItem2InternalConsistency:
    def test_positive_consistent_classification_and_strong_assertions(self) -> None:
        rule_bands = {"Green": (0, 3), "Yellow": (4, 6), "Red": (7, 10)}
        items = [{"name": "slice-1", "score": 4, "band": "Yellow"}]
        audits = [
            {
                "test_name": "test_r2_spec",
                "spec_ref": "R2",
                "requires_value_check": True,
                "has_value_check": True,
                "has_existence_check_only": False,
            }
        ]
        res = check_internal_consistency(
            rule_bands=rule_bands,
            classified_items=items,
            test_assertion_audits=audits,
        )
        assert res.passed is True
        assert len(res.findings) == 0

    def test_negative_sample_224_agent_c_classification_mismatch(self) -> None:
        """真實失敗樣本 #224 Agent C：規則定義 4-6 為 Yellow，卻將 4/10 標為 Green。"""
        rule_bands = {"Green": (0, 3), "Yellow": (4, 6), "Red": (7, 10)}
        items = [{"name": "slice-4", "score": 4, "band": "Green"}]
        res = check_internal_consistency(rule_bands=rule_bands, classified_items=items)
        assert res.passed is False
        assert len(res.findings) == 1
        assert "分數 4 依規則屬於 'Yellow'" in res.findings[0]
        assert "標記為 'Green'" in res.findings[0]

    def test_negative_sample_256_weak_test_assertion(self) -> None:
        """真實失敗樣本 #256：RED 測試宣稱驗證 R2（要求值正確），但僅斷言欄位存在。"""
        audits = [
            {
                "test_name": "test_spec_r2_recovery",
                "spec_ref": "R2",
                "requires_value_check": True,
                "has_value_check": False,
                "has_existence_check_only": True,
            }
        ]
        res = check_internal_consistency(test_assertion_audits=audits)
        assert res.passed is False
        assert any("缺乏語意值比對" in f for f in res.findings)

    def test_exemption_label(self) -> None:
        rule_bands = {"Green": (0, 3), "Yellow": (4, 6)}
        items = [{"name": "s1", "score": 4, "band": "Green"}]
        res = check_internal_consistency(
            rule_bands=rule_bands,
            classified_items=items,
            pr_labels=["policy-exempt:internal-consistency"],
        )
        assert res.passed is True
        assert res.exempted is True


class TestItem3SummaryVsBody:
    def test_positive_summary_matches_body(self) -> None:
        res = check_summary_vs_body(
            summary_claims={"Red": 2},
            body_counts={"Red": 2},
        )
        assert res.passed is True

    def test_negative_sample_224_agent_c_summary_mismatch(self) -> None:
        """真實失敗樣本 #224 Agent C：摘要寫 Red 2 張，內文實際列了 3 張。"""
        res = check_summary_vs_body(
            summary_claims={"Red": 2},
            body_counts={"Red": 3},
        )
        assert res.passed is False
        assert len(res.findings) == 1
        assert "摘要宣稱 2 項，但內文實際包含 3 項" in res.findings[0]

    def test_exemption_label(self) -> None:
        res = check_summary_vs_body(
            summary_claims={"Red": 2},
            body_counts={"Red": 3},
            pr_labels=["policy-exempt:summary-vs-body"],
        )
        assert res.passed is True
        assert res.exempted is True


class TestItem4FactFreshness:
    def test_positive_fresh_facts_and_refs_keyword(self, tmp_path: Path) -> None:
        (tmp_path / ".project-policy.yml").write_text("policy_version: 1.0.15\n")
        res = check_fact_freshness(
            pr_body="Refs #292",
            commit_messages=["feat(quality): add mechanical acceptance Refs #292"],
            referenced_files=[".project-policy.yml"],
            repo_root=tmp_path,
            unresolved_issues=[292],
        )
        assert res.passed is True

    def test_negative_sample_224_agent_b_obsolete_config_filename(self, tmp_path: Path) -> None:
        """真實失敗樣本 #224 Agent B：引用過時檔名 .paul-project.yml。"""
        (tmp_path / ".project-policy.yml").write_text("policy_version: 1.0.15\n")
        res = check_fact_freshness(
            referenced_files=[".paul-project.yml"],
            repo_root=tmp_path,
        )
        assert res.passed is False
        assert any("引用過時設定檔 '.paul-project.yml'" in f for f in res.findings)

    def test_negative_sample_277_commit_msg_closing_keyword_leak(self, tmp_path: Path) -> None:
        """真實失敗樣本 #277：PR body 寫 Refs #277，但 commit message 誤用 Fixes #277。"""
        res = check_fact_freshness(
            pr_body="Refs #277",
            commit_messages=["fix(monitor): readback fix Fixes #277"],
            unresolved_issues=[277],
            repo_root=tmp_path,
        )
        assert res.passed is False
        assert any("Commit msg #1" in f and "Fixes #277" in f for f in res.findings)

    def test_exemption_label(self, tmp_path: Path) -> None:
        res = check_fact_freshness(
            pr_body="Fixes #277",
            unresolved_issues=[277],
            repo_root=tmp_path,
            pr_labels=["policy-exempt:fact-freshness"],
        )
        assert res.passed is True
        assert res.exempted is True


class TestItem5LanguageConventions:
    def test_positive_tw_conventions(self) -> None:
        text = "本專案預設使用繁體中文，測試驗證資料完整，已採納修正。"
        res = check_language_conventions(text_content=text, title="feat(core): 採納語言規範")
        assert res.passed is True

    def test_negative_sample_224_agent_b_non_tw_and_mixed_variants(self) -> None:
        """真實失敗樣本 #224 Agent B：標題用「采」內文用「採」，並包含「驗實資料」「蠻力爆炸」。"""
        text = "測試採用驗實資料，針對蠻力爆炸演算法進行優化。"
        res = check_language_conventions(text_content=text, title="feat(task): 采納 task_type 提案")
        assert res.passed is False
        assert any("簡體/異體字 '采'" in f for f in res.findings)
        assert any("非台灣慣用詞 '驗實資料'" in f for f in res.findings)
        assert any("非台灣慣用詞 '蠻力爆炸'" in f for f in res.findings)

    def test_exemption_label(self) -> None:
        text = "蠻力爆炸"
        res = check_language_conventions(
            text_content=text,
            pr_labels=["policy-exempt:language-conventions"],
        )
        assert res.passed is True
        assert res.exempted is True


class TestItem6UnsubstantiatedQuantification:
    def test_positive_quantification_with_traceable_source(self) -> None:
        text = "工時預估耗時 2 小時 (依據：lesson-20260722 實測數據)。"
        res = check_unsubstantiated_quantification(text_content=text)
        assert res.passed is True

    def test_negative_sample_224_agent_c_fabricated_schedule(self) -> None:
        """真實失敗樣本 #224 Agent C：捏造「總時程 10–14 工作天」無任何依據。"""
        text = "拆解提案完成，估算總時程 10–14 工作天。"
        res = check_unsubstantiated_quantification(text_content=text)
        assert res.passed is False
        assert any("估算宣稱 '拆解提案完成，估算總時程 10–14 工作天。' 缺乏可追溯資料來源" in f for f in res.findings)

    def test_exemption_label(self) -> None:
        text = "估算總時程 10–14 工作天。"
        res = check_unsubstantiated_quantification(
            text_content=text,
            pr_labels=["policy-exempt:unsubstantiated-quantification"],
        )
        assert res.passed is True
        assert res.exempted is True


class TestMechanicalAcceptanceRunnerAndCLI:
    def test_run_acceptance_checks_runner_complete_context(self) -> None:
        """當 6 項檢查所需的 context 齊備時，run_acceptance_checks 回報全 PASS。"""
        context = {
            "text_content": "本專案預設使用繁體中文，測試驗證資料完整，已採納修正。",
            "pr_body": "Refs #292",
            "commit_messages": ["feat: implementation Refs #292"],
            "unresolved_issues": [292],
            "claim_vs_output": {"claimed_count": 0, "residual_findings": []},
            "internal_consistency": {"rule_bands": {"A": (0, 5)}, "classified_items": [{"name": "i1", "score": 2, "band": "A"}]},
            "summary_vs_body": {"summary_claims": {"Fix": 1}, "body_counts": {"Fix": 1}},
        }
        report = run_acceptance_checks(context)
        assert isinstance(report, AcceptanceReport)
        assert report.passed is True
        assert report.has_skipped is False
        assert report.status_summary == "PASS"
        assert len(report.results) == 6

    def test_run_acceptance_checks_runner_partial_context_returns_skipped(self) -> None:
        """當缺少必要 context 時，run_acceptance_checks 不得回報 PASS，而是 report.passed = False 且 has_skipped = True。"""
        context = {
            "text_content": "本專案預設使用繁體中文，測試驗證資料完整，已採納修正。",
            "pr_body": "Refs #292",
        }
        report = run_acceptance_checks(context)
        assert report.passed is False
        assert report.has_skipped is True
        assert report.status_summary == "INCOMPLETE (SKIPPED)"

    def test_cli_e2e_real_sample_277_reports_fail(self, capsys, tmp_path: Path) -> None:
        """端到端測試 1：給定真實失敗樣本 #277 與完整 context，CLI 確實回報 FAIL 並指出具體 finding。"""
        sample_file = tmp_path / "sample_277.txt"
        sample_file.write_text(
            "fix(work): repo rebind 後 monitor 投影與 work authority 跟著走\n\nFixes #277",
            encoding="utf-8",
        )

        exit_code = umbrella_cli.main([
            "mechanical-acceptance",
            "--text-file", str(sample_file),
            "--unresolved-issues", "277",
        ])

        assert exit_code == 1
        output = capsys.readouterr().out
        assert "Mechanical Acceptance Status: FAIL" in output
        assert "- [FAIL] 事實新鮮度 (fact_freshness)" in output
        assert "PR body 使用 closing keyword 'Fixes #277'，但 Issue #277 未完全解決" in output

    def test_cli_e2e_missing_context_reports_skipped(self, capsys, tmp_path: Path) -> None:
        """端到端測試 2：當缺少必要 context (例如只傳 --text-file 含 Fixes #277 但無 unresolved_issues)，CLI 回報 SKIPPED (exit code 2) 而非 PASS。"""
        sample_file = tmp_path / "sample_277.txt"
        sample_file.write_text(
            "fix(work): repo rebind 後 monitor 投影與 work authority 跟著走\n\nFixes #277",
            encoding="utf-8",
        )

        exit_code = umbrella_cli.main([
            "mechanical-acceptance",
            "--text-file", str(sample_file),
        ])

        assert exit_code == 2
        output = capsys.readouterr().out
        assert "Mechanical Acceptance Status: INCOMPLETE (SKIPPED)" in output
        assert "- [SKIPPED] 事實新鮮度 (fact_freshness)" in output
        assert "缺少必要 context: 檢出 closing keyword 'Fixes #277'" in output

    def test_cli_e2e_pr_option_with_fake_gh_runner(self, capsys) -> None:
        """端到端測試 3：使用 --pr <N> 參數與 fake gh 執行器，驗證 CLI 能從 PR 自動取得資料並比對。"""
        from paulsha_cortex.porcelain.mechanical_acceptance import main as porcelain_main

        def fake_gh_runner(args: list[str]) -> str:
            if args[:3] == ["pr", "view", "277"]:
                return json.dumps({
                    "title": "fix(work): repo rebind 後 monitor 投影與 work authority 跟著走",
                    "body": "修正 monitor 投影。 Fixes #277",
                    "labels": [],
                    "commits": [{"message": "fix(work): rebind monitor Fixes #277"}],
                })
            elif args[:3] == ["issue", "view", "277"]:
                return json.dumps({"number": 277, "state": "OPEN"})
            raise ValueError(f"Unexpected gh args: {args}")

        exit_code = porcelain_main(["--pr", "277"], gh_runner=fake_gh_runner)

        assert exit_code == 1
        output = capsys.readouterr().out
        assert "Mechanical Acceptance Status: FAIL" in output
        assert "- [FAIL] 事實新鮮度 (fact_freshness)" in output
        assert "Issue #277 未完全解決" in output
