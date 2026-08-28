from __future__ import annotations

import os


def pid_exists(pid: int) -> bool:
    """Return whether *pid* exists without signalling or mutating it."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False

    if os.name == "nt":
        from ctypes import WinDLL, get_last_error, wintypes

        process_query_limited_information = 0x1000
        error_access_denied = 5
        kernel32 = WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return get_last_error() == error_access_denied

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
