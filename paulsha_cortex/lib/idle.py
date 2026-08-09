import os
from typing import Callable


def system_load_average() -> tuple[float, ...]:
    """Return the system load average when the platform exposes one."""
    probe = getattr(os, "getloadavg", None)
    if probe is None:
        raise OSError("system load average is unavailable on this platform")
    return probe()


def is_idle(
    max_load: float = 1.0,
    probe: Callable[[], tuple[float, ...]] = system_load_average,
) -> bool:
    """Return True when system is considered idle using the 1-minute load average."""
    try:
        result = probe()
        if not isinstance(result, tuple):
            raise TypeError("probe must return a load-average tuple")
        load = float(result[0])
        return load <= float(max_load)
    except (OSError, AttributeError, IndexError):
        return True
