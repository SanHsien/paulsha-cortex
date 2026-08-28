from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_isolated(code: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(ROOT), env.get("PYTHONPATH", "")) if part
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_idle_and_manager_import_without_getloadavg() -> None:
    result = _run_isolated(
        """
import os
if hasattr(os, "getloadavg"):
    del os.getloadavg
from paulsha_cortex.lib.idle import is_idle
from paulsha_cortex.coordinator import manager
assert is_idle() is True
assert callable(manager.run_tick)
"""
    )

    assert result.returncode == 0, result.stderr


def test_manager_daemon_import_without_fcntl() -> None:
    result = _run_isolated(
        """
import builtins
real_import = builtins.__import__
def import_without_fcntl(name, *args, **kwargs):
    if name == "fcntl":
        raise ModuleNotFoundError("blocked fcntl for Windows compatibility test")
    return real_import(name, *args, **kwargs)
builtins.__import__ = import_without_fcntl
from paulsha_cortex.coordinator import manager_daemon
assert callable(manager_daemon.acquire_lock)
"""
    )

    assert result.returncode == 0, result.stderr


def test_lock_file_is_reused_after_release(tmp_path: Path) -> None:
    from paulsha_cortex.coordinator import manager_daemon

    lock_path = tmp_path / "manager.lock"
    held = manager_daemon.acquire_lock(path=lock_path, pid=111)
    assert held is not None

    held.release()

    assert lock_path.is_file()
    reacquired = manager_daemon.acquire_lock(path=lock_path, pid=222)
    assert reacquired is not None
    reacquired.release()


def test_lock_payload_remains_readable_while_held(tmp_path: Path) -> None:
    from paulsha_cortex.control import contract
    from paulsha_cortex.coordinator import manager_daemon

    lock_path = tmp_path / "manager.lock"
    held = manager_daemon.acquire_lock(path=lock_path, pid=111)
    assert held is not None
    try:
        assert contract.read_json(lock_path)["pid"] == 111
    finally:
        held.release()


def test_atomic_json_write_replaces_existing_file(tmp_path: Path) -> None:
    from paulsha_cortex.control import contract

    target = tmp_path / "state.json"
    contract.atomic_write_json(target, {"value": 1})

    contract.atomic_write_json(target, {"value": 2})

    assert contract.read_json(target) == {"value": 2}


def test_pid_probe_does_not_terminate_process() -> None:
    from paulsha_cortex.lib.processes import pid_exists

    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        assert pid_exists(process.pid) is True
        assert process.poll() is None
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_remove_tree_uses_legacy_callback_before_python_312(
    tmp_path: Path, monkeypatch
) -> None:
    from paulsha_cortex.lib import filesystem

    target = tmp_path / "disposable"
    target.mkdir()
    captured: dict[str, object] = {}

    def fake_rmtree(path, **kwargs):
        captured["path"] = path
        captured.update(kwargs)

    monkeypatch.setattr(filesystem.sys, "version_info", (3, 11, 9))
    monkeypatch.setattr(filesystem.shutil, "rmtree", fake_rmtree)

    filesystem.remove_tree(target)

    assert captured["path"] == target
    assert callable(captured["onerror"])
    assert "onexc" not in captured
