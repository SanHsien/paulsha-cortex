from __future__ import annotations

from typing import Any, Mapping, Sequence
from .claim_vs_output import check_claim_vs_output
from .fact_freshness import check_fact_freshness
from .internal_consistency import check_internal_consistency
from .language_conventions import check_language_conventions
from .models import AcceptanceReport, CheckResult
from .summary_vs_body import check_summary_vs_body
from .unsubstantiated_quantification import check_unsubstantiated_quantification


def run_acceptance_checks(context: Mapping[str, Any]) -> AcceptanceReport:
    """執行六項零 model session 機械驗收檢查。"""
    pr_labels = context.get("pr_labels") or ()
    results: list[CheckResult] = []

    # 1. claim_vs_output
    c1 = context.get("claim_vs_output") or {}
    results.append(
        check_claim_vs_output(
            claimed_count=c1.get("claimed_count"),
            claimed_fixed=c1.get("claimed_fixed"),
            claimed_params=c1.get("claimed_params"),
            canonical_params=c1.get("canonical_params"),
            rerun_fn=c1.get("rerun_fn"),
            residual_findings=c1.get("residual_findings"),
            pr_labels=pr_labels,
        )
    )

    # 2. internal_consistency
    c2 = context.get("internal_consistency") or {}
    results.append(
        check_internal_consistency(
            rule_bands=c2.get("rule_bands"),
            classified_items=c2.get("classified_items"),
            test_assertion_audits=c2.get("test_assertion_audits"),
            pr_labels=pr_labels,
        )
    )

    # 3. summary_vs_body
    c3 = context.get("summary_vs_body") or {}
    results.append(
        check_summary_vs_body(
            summary_claims=c3.get("summary_claims"),
            body_counts=c3.get("body_counts"),
            text_content=c3.get("text_content") or context.get("text_content"),
            pr_labels=pr_labels,
        )
    )

    # 4. fact_freshness
    c4 = context.get("fact_freshness") or {}
    results.append(
        check_fact_freshness(
            text_content=c4.get("text_content") or context.get("text_content") or "",
            pr_body=c4.get("pr_body") or context.get("pr_body") or "",
            commit_messages=c4.get("commit_messages") or context.get("commit_messages") or (),
            referenced_files=c4.get("referenced_files") or (),
            repo_root=c4.get("repo_root") or context.get("repo_root"),
            unresolved_issues=c4.get("unresolved_issues") or (),
            pr_labels=pr_labels,
        )
    )

    # 5. language_conventions
    c5 = context.get("language_conventions") or {}
    text_for_lang = c5.get("text_content") or context.get("text_content") or ""
    if text_for_lang:
        results.append(
            check_language_conventions(
                text_content=text_for_lang,
                title=c5.get("title") or context.get("title") or "",
                repo_name=c5.get("repo_name") or context.get("repo_name") or "hamanpaul/paulsha-cortex",
                pr_labels=pr_labels,
            )
        )
    else:
        results.append(
            CheckResult(
                check_id="language_conventions",
                check_name="語言規範",
                passed=True,
            )
        )

    # 6. unsubstantiated_quantification
    c6 = context.get("unsubstantiated_quantification") or {}
    text_for_quant = c6.get("text_content") or context.get("text_content") or ""
    if text_for_quant:
        results.append(
            check_unsubstantiated_quantification(
                text_content=text_for_quant,
                pr_labels=pr_labels,
            )
        )
    else:
        results.append(
            CheckResult(
                check_id="unsubstantiated_quantification",
                check_name="禁止無依據量化",
                passed=True,
            )
        )

    all_passed = all(r.passed for r in results)
    return AcceptanceReport(passed=all_passed, results=results)
