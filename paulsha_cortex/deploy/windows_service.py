"""Unprivileged per-user Windows service backend for Cortex."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from paulsha_cortex.lib.file_lock import try_lock, unlock
from paulsha_cortex.lib.processes import pid_exists


COMPONENTS = ("manager", "monitor")


@dataclass(frozen=True)
class TaskResult:
    returncode: int
    message: str


def available() -> bool:
    return os.name == "nt"


def _home() -> Path:
    return Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or Path.home()).expanduser()


def startup_directory() -> Path:
    appdata = os.environ.get("APPDATA")
    roaming = Path(appdata) if appdata else _home() / "AppData" / "Roaming"
    return roaming / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _bootstrap_runtime_dir() -> Path:
    return _home() / ".agents" / "core" / "runtime"


def _service_dir(instance: str) -> Path:
    return _bootstrap_runtime_dir() / "windows-services"


def _manifest_path(instance: str) -> Path:
    return _service_dir(instance) / f"{instance}.json"


def installed(instance: str) -> bool:
    path = _manifest_path(instance)
    return path.is_file() and not path.is_symlink()


def _component_pid_path(instance: str, component: str) -> Path:
    return _service_dir(instance) / f"{instance}-{component}.pid"


def _component_guard_path(instance: str, component: str) -> Path:
    return _service_dir(instance) / f".{instance}-{component}.lock"


def runtime_env_path(instance: str) -> Path:
    return _bootstrap_runtime_dir() / f"{instance}-manager.env"


def log_path(instance: str, component: str) -> Path:
    values = _read_env(runtime_env_path(instance))
    agents_root = Path(values.get("PSC_AGENTS_ROOT", _home() / ".agents"))
    return agents_root / "log" / f"{instance}-{component}.log"


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file() or path.is_symlink():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        key, separator, value = line.partition("=")
        if separator and key:
            values[key] = value
    return values


def _load_manifest(instance: str) -> dict[str, str]:
    path = _manifest_path(instance)
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def install_startup(
    *,
    instance: str,
    repo_root: Path,
    runtime_dir: Path,
    python_executable: Path | None = None,
) -> TaskResult:
    executable = Path(python_executable or sys.executable).resolve()
    pythonw = executable.with_name("pythonw.exe")
    launcher_executable = pythonw if pythonw.is_file() else executable
    service_dir = runtime_dir / "windows-services"
    service_dir.mkdir(parents=True, exist_ok=True)
    startup = startup_directory()
    startup.mkdir(parents=True, exist_ok=True)
    launcher = startup / f"paulsha-cortex-{instance}.cmd"
    command = subprocess.list2cmdline(
        [
            str(launcher_executable),
            "-m",
            "paulsha_cortex.deploy.windows_service",
            "launch",
            "--instance",
            instance,
        ]
    )
    launcher.write_text(f"@echo off\nstart \"\" /min {command}\n", encoding="utf-8")
    manifest = {
        "schema": "cortex-windows-service/v1",
        "instance": instance,
        "python": str(executable),
        "repo_root": str(repo_root.resolve()),
        "startup_launcher": str(launcher),
    }
    (service_dir / f"{instance}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return TaskResult(0, f"installed Windows per-user startup launcher: {launcher}")


def _read_component_pid(instance: str, component: str) -> int | None:
    path = _component_pid_path(instance, component)
    if not path.is_file() or path.is_symlink():
        return None
    try:
        pid = int(path.read_text(encoding="ascii").strip())
    except (OSError, UnicodeError, ValueError):
        return None
    return pid if pid > 0 else None


def query_processes(instance: str) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for component in COMPONENTS:
        pid = _read_component_pid(instance, component)
        running = pid_exists(pid) if pid is not None else False
        rows[component] = {
            "pid": pid,
            "running": running,
            "status": "running" if running else "stale" if pid is not None else "stopped",
        }
    return rows


def _start_component(component: str, *, instance: str) -> bool:
    pid = _read_component_pid(instance, component)
    if pid is not None and pid_exists(pid):
        return False
    manifest = _load_manifest(instance)
    if not manifest:
        raise RuntimeError(f"Windows service is not installed for {instance}")
    executable = str(manifest.get("python") or sys.executable)
    repo_root = Path(str(manifest.get("repo_root") or Path.cwd())).resolve()
    argv = [
        executable,
        "-m",
        "paulsha_cortex.deploy.windows_service",
        "run",
        component,
        "--instance",
        instance,
    ]
    creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
        subprocess, "DETACHED_PROCESS", 0
    )
    process = subprocess.Popen(
        argv,
        cwd=str(repo_root),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creation_flags,
    )
    pid_path = _component_pid_path(instance, component)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(process.pid), encoding="ascii")
    for _ in range(20):
        returncode = process.poll()
        if returncode is not None:
            if _read_component_pid(instance, component) == process.pid and pid_path.exists():
                pid_path.unlink()
            raise RuntimeError(
                f"{component} exited during startup with exit code {returncode}; "
                f"see {log_path(instance, component)}"
            )
        time.sleep(0.05)
    return True


def _pid_matches_component(pid: int, *, instance: str, component: str) -> bool:
    command = (
        f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}' "
        "-ErrorAction SilentlyContinue).CommandLine"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=10,
    )
    command_line = result.stdout or ""
    return (
        result.returncode == 0
        and "paulsha_cortex.deploy.windows_service" in command_line
        and f"run {component}" in command_line
        and f"--instance {instance}" in command_line
    )


def _stop_component(component: str, *, instance: str) -> None:
    pid_path = _component_pid_path(instance, component)
    pid = _read_component_pid(instance, component)
    if pid is None or not pid_exists(pid):
        if pid_path.exists() or pid_path.is_symlink():
            pid_path.unlink()
        return
    if not _pid_matches_component(pid, instance=instance, component=component):
        raise RuntimeError(f"refusing to stop unverified PID {pid} for {component}")
    result = subprocess.run(
        ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or f"taskkill failed for {pid}").strip())
    for _ in range(20):
        if not pid_exists(pid):
            break
        time.sleep(0.05)
    if not pid_exists(pid) and (pid_path.exists() or pid_path.is_symlink()):
        pid_path.unlink()


def control_processes(command: str, *, instance: str) -> TaskResult:
    if command not in {"start", "stop", "restart"}:
        raise ValueError(f"unsupported Windows service command: {command}")
    failures: list[str] = []
    if command in {"stop", "restart"}:
        for component in COMPONENTS:
            try:
                _stop_component(component, instance=instance)
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                failures.append(str(error))
    if command in {"start", "restart"} and not failures:
        started: list[str] = []
        for component in COMPONENTS:
            try:
                if _start_component(component, instance=instance):
                    started.append(component)
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                failures.append(str(error))
                for started_component in reversed(started):
                    try:
                        _stop_component(started_component, instance=instance)
                    except (OSError, RuntimeError, subprocess.SubprocessError) as rollback_error:
                        failures.append(f"rollback failed: {rollback_error}")
                break
    return TaskResult(
        1 if failures else 0,
        "; ".join(failures) if failures else f"{command} completed for {instance}",
    )


def uninstall_startup(instance: str) -> TaskResult:
    stopped = control_processes("stop", instance=instance)
    if stopped.returncode != 0:
        return stopped
    manifest = _load_manifest(instance)
    launcher_value = manifest.get("startup_launcher")
    if isinstance(launcher_value, str):
        launcher = Path(launcher_value)
        if launcher.exists() or launcher.is_symlink():
            launcher.unlink()
    for path in (
        _manifest_path(instance),
        *(_component_pid_path(instance, component) for component in COMPONENTS),
        *(_component_guard_path(instance, component) for component in COMPONENTS),
    ):
        if path.exists() or path.is_symlink():
            path.unlink()
    return TaskResult(0, f"uninstalled Windows per-user service for {instance}")


def run_component(component: str, *, instance: str) -> int:
    if component not in COMPONENTS:
        raise ValueError(f"unsupported Windows service component: {component}")
    service_dir = _service_dir(instance)
    service_dir.mkdir(parents=True, exist_ok=True)
    guard_path = _component_guard_path(instance, component)
    guard_fd = os.open(guard_path, os.O_RDWR | os.O_CREAT, 0o600)
    locked = try_lock(guard_fd)
    if not locked:
        os.close(guard_fd)
        return 0
    pid_path = _component_pid_path(instance, component)
    pid_path.write_text(str(os.getpid()), encoding="ascii")
    env = _read_env(runtime_env_path(instance))
    os.environ.update(env)
    repo_root = Path(env.get("PSC_REPO_ROOT", Path.cwd())).resolve()
    os.chdir(repo_root)
    target_log = log_path(instance, component)
    target_log.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target_log.open("a", encoding="utf-8", buffering=1) as stream:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                try:
                    if component == "manager":
                        from paulsha_cortex.coordinator import manager_daemon

                        specs_dir = env.get("PSC_MANAGER_SPECS_DIR")
                        argv = ["--specs-dir", specs_dir] if specs_dir else []
                        return int(manager_daemon.main(argv) or 0)
                    from paulsha_cortex.monitor.__main__ import main as monitor_main

                    return int(monitor_main([]) or 0)
                except Exception:
                    traceback.print_exc()
                    return 1
    finally:
        if _read_component_pid(instance, component) == os.getpid() and pid_path.exists():
            pid_path.unlink()
        unlock(guard_fd)
        os.close(guard_fd)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m paulsha_cortex.deploy.windows_service")
    sub = parser.add_subparsers(dest="command", required=True)
    launch = sub.add_parser("launch")
    launch.add_argument("--instance", required=True)
    run = sub.add_parser("run")
    run.add_argument("component", choices=COMPONENTS)
    run.add_argument("--instance", required=True)
    args = parser.parse_args(argv)
    if args.command == "launch":
        return control_processes("start", instance=args.instance).returncode
    return run_component(args.component, instance=args.instance)


if __name__ == "__main__":
    raise SystemExit(main())
