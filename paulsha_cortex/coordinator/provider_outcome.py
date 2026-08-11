"""#384：executor/provider 失敗的 typed 分類與 bounded recovery 的共用語意。

Root cause（見 issue #384 2026-08-10 複驗 comment）：`completion.classify_completion`
只有 exited/failed 兩值，job registry 也只有 status/exit_code；下游（slice lane
`manager.py` 的 build-phase failure、workflow lane 的 job-failed 分支）因此一律
把任何 executor 失敗壓平成寫死的 ``"builder-failed"``／``"job-failed"``＋
``needs_human``——auth 失效、rate limit、暫時性網路錯誤、內容政策拒答，全部
得到同一種（無分類、無 retry、無 backoff）處置。

本模組不重造分類器：複用 #369 的 :func:`executor_auth.classify_cli_output`
（rate_limited／logged_out／ok／unknown，且已修好 rate-limit 必須先於 login
判定的順序）與 #370 的 :mod:`paulsha_cortex.github_rate_limit`（獨立的
rate-limit／auth 訊號正則，覆蓋 executor_auth 未涵蓋的措辭），在其上疊
quota／transient／content 三類新訊號，統一成一個
:class:`ProviderFailureClassification`。

**中間 authority 等級**（解 issue 內註記的 plan 矛盾——規則 5「stderr 關鍵字只做
hint 不升 authoritative」vs. recovery matrix 期待 rate_limited 在 copilot
這種「限流只有 stderr 文字、無 structured code」的 executor 上仍能觸發 retry）：

- :data:`SignalAuthority.STRUCTURED` —— 來自結構化訊號（明確 HTTP status
  code、JSON 錯誤欄位）。可驅動任何決策，含 policy 層決策。
- :data:`SignalAuthority.TEXT_SIGNAL` —— 來自 CLI stdout/stderr 文字關鍵字比對
  （本模組與 executor_auth／github_rate_limit 的既有 regex）。比 HINT
  強——足以驅動**有界、可逆**的動作（這一輪 bounded retry、在既有 candidate
  順序上 re-route），但**不足以**驅動不可逆或 policy 層決策（放寬
  independence domain、永久拉黑 provider、略過人工複核）。這正是規則 5 真正想
  擋的：不是「stderr 訊號不能用」，是「stderr 訊號不能升級到需要 structured
  authority 的動作」。retry／re-route 從未要求 structured authority，故兩者
  不矛盾。
- :data:`SignalAuthority.HINT` —— exit code 非零但無任何已知訊號匹配。只供
  人類判讀，不驅動任何自動決策（既不 retry 也不變更 gate_reason 之外的欄位）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from paulsha_cortex.github_rate_limit import is_auth_signal, is_rate_limit_signal

from . import executor_auth

__all__ = [
    "ProviderOutcome",
    "SignalAuthority",
    "RETRYABLE_OUTCOMES",
    "ProviderFailureClassification",
    "classify_provider_failure",
    "classification_from_job",
    "read_log_tail",
]


class ProviderOutcome(str, Enum):
    """executor/provider 失敗的分類結果。"""

    AUTH = "auth"
    RATE_LIMITED = "rate_limited"
    QUOTA = "quota"
    TRANSIENT = "transient"
    CONTENT = "content"
    UNKNOWN = "unknown"


class SignalAuthority(str, Enum):
    """分類結果的可信等級——決定這個結果可以驅動多強的決策（見模組 docstring）。"""

    STRUCTURED = "structured"
    TEXT_SIGNAL = "text_signal"
    HINT = "hint"


# 只有這兩類「重試大概率會解決」：rate limit 會隨時間窗重置、transient 是
# 網路/服務暫時性錯誤。auth／content／quota／unknown 盲目重試不會改善結果
# （auth 需要人工重新登入；content 是模型對這個 prompt 的決定，重跑同一個
# candidate 不會變；quota 通常是固定週期額度，短時間內重試沒有意義；unknown
# 沒有訊號可支持任何自動決策）。
RETRYABLE_OUTCOMES = frozenset({ProviderOutcome.RATE_LIMITED, ProviderOutcome.TRANSIENT})

_PROVIDER_OUTCOME_FIELDS = frozenset({"outcome", "authority", "reason", "retryable"})

# Quota：固定週期用量上限（月配額、bulk usage limit），與 rate_limit（滑動時間窗、
# 通常數十秒到數分鐘內重置）語意不同，值得分開分類以利未來對 quota 採不同的
# backoff 策略（本票僅分類，不對 quota 做 bounded retry——見 RETRYABLE_OUTCOMES）。
#
# 刻意不收 "quota exceeded"／"usage limit" 這兩個措辭：`executor_auth`
# 複用的 rate-limit 正則（見 executor_auth._RATE_LIMIT_RE／
# github_rate_limit._RATE_LIMIT_PATTERN）已經把它們算進 rate-limit（兩者
# 語意接近——都是「等時間窗過了就會恢復」），而 rate-limit 判定排在本模組
# quota 檢查之前，故這兩個措辭實際上永遠命中不到這裡；本類別只收「不是等
# 時間窗、而是要人工處理（帳單、方案升級）」的措辭，避免死碼與誤導。
_QUOTA_RE = re.compile(
    r"""
    monthly\ limit
    | plan\ limit
    | billing
    | insufficient\ credits?
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Transient：網路/服務暫時性錯誤，與 rate limit 不同——這裡沒有「額度」語意，
# 純粹是這一次呼叫失敗，重試通常會成功。
_TRANSIENT_RE = re.compile(
    r"""
    connection\ reset
    | econnreset
    | timed?\ ?out
    | \btimeout\b
    | temporarily\ unavailable
    | service\ unavailable
    | bad\ gateway
    | gateway\ time-?out
    | \b50[0234]\b
    | network\ error
    | dns\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Content：模型基於內容政策拒答，屬於「這次呼叫本身不該被無腦重試」的類別。
_CONTENT_RE = re.compile(
    r"""
    content\ (policy|filtered)
    | refus(e|ed|ing)\ to\ (assist|help|continue)
    | cannot\ assist
    | violates\ (our|the)\ (usage\ )?polic
    | safety\ (guidelines|system|filter)
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True)
class ProviderFailureClassification:
    """一次 executor 失敗的分類結果（純資料）。"""

    outcome: ProviderOutcome
    authority: SignalAuthority
    reason: str

    @property
    def retryable(self) -> bool:
        """是否適合驅動 bounded retry——見模組 docstring 的 authority 分級。"""

        return self.authority is not SignalAuthority.HINT and self.outcome in RETRYABLE_OUTCOMES

    def to_dict(self) -> dict[str, object]:
        return {
            "outcome": self.outcome.value,
            "authority": self.authority.value,
            "reason": self.reason,
            "retryable": self.retryable,
        }

    @classmethod
    def from_dict(cls, payload: object) -> "ProviderFailureClassification | None":
        """讀回既有 job/manifest 上存的分類結果；格式不符一律回 None（fail-soft，
        不阻塞既有讀路徑——這只是輔助分類，不是授權欄位）。
        """

        if not isinstance(payload, Mapping) or set(payload) != _PROVIDER_OUTCOME_FIELDS:
            return None
        outcome = payload.get("outcome")
        authority = payload.get("authority")
        reason = payload.get("reason")
        try:
            outcome_enum = ProviderOutcome(outcome)
            authority_enum = SignalAuthority(authority)
        except ValueError:
            return None
        if not isinstance(reason, str) or not reason:
            return None
        return cls(outcome=outcome_enum, authority=authority_enum, reason=reason)


def classify_provider_failure(*, exit_code: int, output: str | None) -> ProviderFailureClassification:
    """把一次 executor 失敗的 (exit_code, 合併 stdout/stderr 文字) 分類成 typed outcome。

    Rate limit 判定必須排在 auth 判定之前（沿用 #369/#370 的教訓：GitHub／
    provider 的限流訊息常同時帶有 "authenticate"／"login" 字樣）。呼叫端只在
    確認這是一次失敗（exit_code != 0 或呼叫端已知 status == "failed"）時呼叫
    本函式；exit_code == 0 時仍會回傳一個防禦性的 UNKNOWN/HINT 分類而不拋錯，
    避免呼叫端誤用時整條鏈路炸掉。
    """

    text = output or ""
    if exit_code == 0:
        return ProviderFailureClassification(
            ProviderOutcome.UNKNOWN,
            SignalAuthority.HINT,
            "exit code 0 -- classify_provider_failure 不應被呼叫在成功案例",
        )

    cli_status, cli_detail = executor_auth.classify_cli_output(exit_code, text)

    if cli_status == "rate_limited" or is_rate_limit_signal(text):
        return ProviderFailureClassification(
            ProviderOutcome.RATE_LIMITED,
            SignalAuthority.TEXT_SIGNAL,
            f"rate limit signal detected in executor output ({cli_detail})",
        )
    if _QUOTA_RE.search(text):
        return ProviderFailureClassification(
            ProviderOutcome.QUOTA,
            SignalAuthority.TEXT_SIGNAL,
            "quota signal detected in executor output",
        )
    if cli_status == "logged_out" or is_auth_signal(text):
        return ProviderFailureClassification(
            ProviderOutcome.AUTH,
            SignalAuthority.TEXT_SIGNAL,
            f"auth/login signal detected in executor output ({cli_detail})",
        )
    if _CONTENT_RE.search(text):
        return ProviderFailureClassification(
            ProviderOutcome.CONTENT,
            SignalAuthority.TEXT_SIGNAL,
            "content-policy signal detected in executor output",
        )
    if _TRANSIENT_RE.search(text):
        return ProviderFailureClassification(
            ProviderOutcome.TRANSIENT,
            SignalAuthority.TEXT_SIGNAL,
            "transient/network signal detected in executor output",
        )
    return ProviderFailureClassification(
        ProviderOutcome.UNKNOWN,
        SignalAuthority.HINT,
        f"no definitive signal (exit {exit_code})",
    )


def classification_from_job(job: Mapping[str, object]) -> ProviderFailureClassification | None:
    """從 job registry row 讀回既有的分類結果（`Dispatcher._finalize_headless`
    在 finalize 當下寫入的 ``job["provider_outcome"]``）。找不到／格式不符一律
    回 None——呼叫端 fail-soft 退回既有無分類行為，不是 fail-closed 授權欄位。
    """

    return ProviderFailureClassification.from_dict(job.get("provider_outcome"))


def read_log_tail(log_path: str | None, *, max_bytes: int = 65536) -> str | None:
    """讀 headless job log 檔尾端至多 ``max_bytes`` bytes，供分類用。

    只讀尾端而非整檔：日誌可能很大（長時間 session），分類只關心最後出現的
    錯誤訊號；有界讀取避免熱路徑上的大檔 I/O 成本。壞檔/缺檔一律回 None
    （fail-soft——讀不到 log 不該讓 finalize 整條路徑炸掉，只是分類退化成
    UNKNOWN/HINT）。
    """

    if not log_path:
        return None
    try:
        with open(log_path, "rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            raw = handle.read()
    except OSError:
        return None
    return raw.decode("utf-8", errors="replace")
