"""Per-provider spawn admission limiter（issue #381）。

Root cause：`autonomy.dispatch_ready` 的 fan-out 迴圈與 workflow lane（periodic
tick 逐一 resume ongoing run）背靠背 spawn 同一 provider 的多個 executor——例如
copilot 啟動時連續探測 GitHub `/user` 約 6-7 次做 credential/login 驗證。這個
quota bucket 與 `gh api rate_limit` 回報的 core bucket 是分開的，既有診斷
（含 `cortex doctor`）看不到，瞬間併發啟動會把它打爆，執行期的 token 其實
完好，卻被回報成「需要重新登入」。

瓶頸只發生在**啟動瞬間**的 credential probe burst，不是 builder/reviewer 的
執行期，因此這裡刻意不做「整個 job 生命週期」的併發上限或全域序列化：
``admit()`` 只在呼叫的那一刻可能 block（同 provider 尚未跑滿最小間隔時），
一旦回傳即視為「已釋放」，不需要對應的 release()，也不會拖慢後續長時間執行。
不同 provider 各自維護獨立時間軸，彼此不阻塞——同時派工 codex 與 claude
不會因為 copilot 正在等待而被拖慢。

``spawn_admission=None``（不注入）在每一層都刻意解析為零間隔的 no-op
limiter，效果等同完全不接線——這樣現有呼叫端／測試在不知情的情況下傳入
`None`（或乾脆不傳）不會意外觸發真正的 wall-clock sleep。真正的生產預設值
只在 `manager_daemon.main()`（唯一啟動長駐 daemon 的進場點）透過
`build_default_limiter()` 明確建構，再顯式往下注入到 fanout 與 workflow 兩條
lane 共用的同一個 instance。
"""

from __future__ import annotations

import os
import threading
import time
from typing import Callable, Mapping

# 5000/hr 的 core rate limit 遠比這寬鬆；#381 撞到的是 copilot 啟動時打的
# GitHub `/user` 端點，其視窗以分鐘計（issue 證據：reset 落在約 5.5 分鐘後）。
# 2 秒的最小間隔足以把單次 dispatch_ready 迴圈內的背靠背 spawn 錯開，不會讓
# 正常規模（個位數 ready slice）的 fan-out 顯著變慢；可用
# PSC_SPAWN_MIN_INTERVAL_SECONDS 覆寫，0 停用節流。
DEFAULT_MIN_INTERVAL_SECONDS = 2.0

_ENV_DEFAULT_INTERVAL = "PSC_SPAWN_MIN_INTERVAL_SECONDS"
_ENV_PROVIDER_PREFIX = "PSC_SPAWN_MIN_INTERVAL_SECONDS__"
_DEFAULT_PROVIDER = "default"


class SpawnAdmissionLimiter:
    """Per-provider 最小啟動間隔（token-bucket 風格的 min-interval stagger）。

    ``admit(provider)``：呼叫端即將 spawn 前呼叫一次。若同一 provider 上次
    admit 後尚未跑滿 ``interval_for(provider)`` 秒，內部 sleep 補足差額，
    否則立即回傳（不等待）。回傳值為實際等待秒數，供呼叫端／測試觀測。

    Reservation（下一個可 admit 的時刻）在鎖內原子完成，sleep 則在鎖外執行：
    這樣同一 provider 的並發 admit() 呼叫仍會被正確序列化（避免兩者都讀到
    同一個「上次時刻」而各自算出過短的等待），但不同 provider 的 admit()
    不會被彼此的 sleep 卡住鎖。
    """

    def __init__(
        self,
        *,
        min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
        provider_overrides: Mapping[str, float] | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_interval_seconds = max(0.0, float(min_interval_seconds))
        self._overrides: dict[str, float] = {
            str(provider): max(0.0, float(seconds))
            for provider, seconds in (provider_overrides or {}).items()
        }
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._last_admitted_at: dict[str, float] = {}

    def interval_for(self, provider: str) -> float:
        return self._overrides.get(provider, self.min_interval_seconds)

    def admit(self, provider: str | None) -> float:
        key = provider if isinstance(provider, str) and provider else _DEFAULT_PROVIDER
        interval = self.interval_for(key)
        with self._lock:
            now = self._clock()
            last = self._last_admitted_at.get(key)
            wait_seconds = 0.0
            if last is not None and interval > 0.0:
                elapsed = now - last
                if elapsed < interval:
                    wait_seconds = interval - elapsed
            self._last_admitted_at[key] = now + wait_seconds
        if wait_seconds > 0.0:
            self._sleep(wait_seconds)
        return wait_seconds


def resolve_provider(
    *,
    identity: object | None = None,
    executor: str | None = None,
    launcher: object | None = None,
    default: str = _DEFAULT_PROVIDER,
) -> str:
    """解出這次 spawn 要記在哪個 provider bucket：

    1) 已解析的 model identity（``identity.executor``，例如 slice frontmatter
       宣告 executor/model_id、或 workflow card 已選定的 identity）；
    2) 呼叫端明確傳入的 executor 字面值（例如 slice meta 的 ``executor`` 欄，
       即使該次未觸發 identity 解析）；
    3) launcher 自報的 ``executor`` 屬性（``SubprocessLauncher`` 公開此屬性）；
    4) 都拿不到時退回共用的 ``default`` bucket——仍會被節流，只是失去
       per-provider 的精細度（同一次呼叫通常只有一顆注入的 launcher，實務上
       等同該 launcher 的真實 provider）。
    """
    identity_executor = getattr(identity, "executor", None)
    if isinstance(identity_executor, str) and identity_executor:
        return identity_executor
    if isinstance(executor, str) and executor:
        return executor
    launcher_executor = getattr(launcher, "executor", None)
    if isinstance(launcher_executor, str) and launcher_executor:
        return launcher_executor
    return default


def resolve_limiter(spawn_admission: "SpawnAdmissionLimiter | None") -> "SpawnAdmissionLimiter":
    """``spawn_admission=None``（未注入）一律解析為零間隔 no-op limiter。

    刻意不用 process-wide 單例：每個未注入的呼叫端各自拿一個全新、零狀態的
    no-op instance，行為上與「完全沒有這個參數」等價，讓現有呼叫端／整套
    既有測試不會因為新增這個可選參數而意外背上真正的 wall-clock sleep。
    真正會節流的 limiter 一律由呼叫者顯式建構並注入（見 module docstring）。
    """
    if spawn_admission is not None:
        return spawn_admission
    return SpawnAdmissionLimiter(min_interval_seconds=0.0)


def _float_env(env: Mapping[str, str], name: str) -> float | None:
    raw = env.get(name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def build_default_limiter(
    *,
    min_interval_seconds: float | None = None,
    env: Mapping[str, str] | None = None,
) -> SpawnAdmissionLimiter:
    """production 進場點（``manager_daemon.main``）用的真實 limiter 建構。

    優先序：呼叫端明確傳入的 ``min_interval_seconds`` ＞
    ``PSC_SPAWN_MIN_INTERVAL_SECONDS`` 環境變數 ＞ 內建預設
    ``DEFAULT_MIN_INTERVAL_SECONDS``。per-provider 覆寫讀
    ``PSC_SPAWN_MIN_INTERVAL_SECONDS__<PROVIDER>``（大小寫不敏感，內部一律
    正規化成小寫比對 ``resolve_provider`` 回傳的 executor 名稱）。
    """
    active_env = os.environ if env is None else env
    resolved_default = min_interval_seconds
    if resolved_default is None:
        resolved_default = _float_env(active_env, _ENV_DEFAULT_INTERVAL)
    if resolved_default is None:
        resolved_default = DEFAULT_MIN_INTERVAL_SECONDS

    overrides: dict[str, float] = {}
    for key, value in active_env.items():
        if not key.startswith(_ENV_PROVIDER_PREFIX):
            continue
        provider = key[len(_ENV_PROVIDER_PREFIX):].strip().lower()
        if not provider:
            continue
        try:
            overrides[provider] = float(value)
        except ValueError:
            continue

    return SpawnAdmissionLimiter(
        min_interval_seconds=resolved_default,
        provider_overrides=overrides,
    )
