from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from paulsha_cortex.deploy import installer, windows_service
from paulsha_cortex.porcelain import service


def _completed(argv: list[str], returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode, stdout="ok", stderr="")


def test_install_startup_writes_per_user_launcher_without_external_registration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    startup = tmp_path / "Startup"
    monkeypatch.setattr(windows_service, "startup_directory", lambda: startup)

    result = windows_service.install_startup(
        instance="beta",
        repo_root=tmp_path / "repo with spaces",
        runtime_dir=tmp_path / "runtime",
        python_executable=tmp_path / "Python 3" / "python.exe",
    )

    assert result.returncode == 0
    launcher = startup / "paulsha-cortex-beta.cmd"
    text = launcher.read_text(encoding="utf-8")
    assert "paulsha_cortex.deploy.windows_service launch" in text
    assert "--instance beta" in text
    assert str(tmp_path / "Python 3" / "python.exe") in text
    assert (tmp_path / "runtime" / "windows-services" / "beta.json").is_file()


def test_control_processes_restart_is_stop_then_start(
    monkeypatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        windows_service,
        "_stop_component",
        lambda component, *, instance: calls.append(("stop", component)) or None,
    )
    monkeypatch.setattr(
        windows_service,
        "_start_component",
        lambda component, *, instance: calls.append(("start", component)) or None,
    )

    result = windows_service.control_processes("restart", instance="beta")

    assert result.returncode == 0
    assert calls == [
        ("stop", "manager"),
        ("stop", "monitor"),
        ("start", "manager"),
        ("start", "monitor"),
    ]


def test_query_processes_reports_live_and_stale_pid_files(monkeypatch) -> None:
    monkeypatch.setattr(windows_service, "_read_component_pid", lambda instance, component: 11 if component == "manager" else 22)
    monkeypatch.setattr(windows_service, "pid_exists", lambda pid: pid == 11)

    assert windows_service.query_processes("beta") == {
        "manager": {"pid": 11, "running": True, "status": "running"},
        "monitor": {"pid": 22, "running": False, "status": "stale"},
    }


def test_start_component_rejects_process_that_exits_during_startup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest = {
        "python": str(tmp_path / "python.exe"),
        "repo_root": str(tmp_path),
    }
    pid_path = tmp_path / "manager.pid"

    class ExitedProcess:
        pid = 321

        @staticmethod
        def poll() -> int:
            return 1

    monkeypatch.setattr(windows_service, "_load_manifest", lambda instance: manifest)
    monkeypatch.setattr(
        windows_service,
        "_component_pid_path",
        lambda instance, component: pid_path,
    )
    monkeypatch.setattr(windows_service.subprocess, "Popen", lambda *args, **kwargs: ExitedProcess())

    with pytest.raises(RuntimeError, match="exited during startup"):
        windows_service._start_component("manager", instance="beta")

    assert not pid_path.exists()


def test_installer_registers_native_windows_tasks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    home.mkdir()
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    seen: dict[str, object] = {}

    def fake_install_startup(**kwargs) -> windows_service.TaskResult:
        seen.update(kwargs)
        return windows_service.TaskResult(0, "tasks registered")

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(installer, "_is_windows", lambda: True)
    monkeypatch.setattr(windows_service, "available", lambda: True)
    monkeypatch.setattr(windows_service, "install_startup", fake_install_startup)
    monkeypatch.setattr(
        installer.hook_reconcile,
        "reconcile_codex_hooks",
        lambda path: type("Result", (), {"detail": "unchanged"})(),
    )

    result = installer.install_service_result("beta", 120, repo.resolve())

    assert result.mode == "windows-startup"
    assert result.exit_code == 0
    assert seen["instance"] == "beta"
    assert seen["repo_root"] == repo.resolve()
    assert seen["runtime_dir"] == home / ".agents" / "core" / "runtime"
    env = (home / ".agents" / "core" / "runtime" / "beta-manager.env").read_text(
        encoding="utf-8"
    )
    assert "PSC_MANAGER_INTERVAL_SECONDS=120" in env


def test_porcelain_lifecycle_uses_windows_process_backend(monkeypatch, capsys) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(windows_service, "available", lambda: True)
    monkeypatch.setattr(
        windows_service,
        "control_processes",
        lambda command, *, instance: (
            calls.append((command, instance))
            or windows_service.TaskResult(0, "ok")
        ),
    )
    monkeypatch.setattr(
        service,
        "_status_payload",
        lambda instance: {"instance": instance, "mode": "windows-startup"},
    )

    assert service._run_lifecycle("restart", instance="beta", json_output=True) == 0

    assert calls == [("restart", "beta")]
    assert '"mode": "windows-startup"' in capsys.readouterr().out
