from __future__ import annotations

from pathlib import Path

import pytest

from paulsha_cortex import cli
from paulsha_cortex.control import constants


def test_control_lock_path_prints_constants_lock_path(monkeypatch, tmp_path, capsys):
    """issue #375：shell wrapper 與 daemon 過去各自硬寫一套 lock 路徑解析邏輯，
    agents_root 不同時會分歧（wrapper 認養到別的 instance 的 pid）。`cortex control
    lock-path` 是兩端共用的單一來源；必須直接印出 `constants.lock_path()`，不能自己
    另外組一套路徑規則。"""
    monkeypatch.setenv("PSC_CONTROL_ROOT", str(tmp_path / "ctl"))

    assert cli.main(["control", "lock-path"]) == 0

    out = capsys.readouterr().out.strip()
    assert out == str(constants.lock_path())
    assert out == str(tmp_path / "ctl" / "manager.lock")


def test_control_lock_path_follows_agents_root_and_instance(monkeypatch, tmp_path, capsys):
    """沒有明確 PSC_CONTROL_ROOT 時走 PSC_AGENTS_ROOT 推導（與 config/runtime.py
    的解析鏈同源），不是另一套硬寫預設。"""
    monkeypatch.delenv("PSC_CONTROL_ROOT", raising=False)
    monkeypatch.setenv("PSC_AGENTS_ROOT", str(tmp_path / "agents"))

    assert cli.main(["control", "lock-path"]) == 0

    out = capsys.readouterr().out.strip()
    assert out == str(tmp_path / "agents" / "control" / "manager.lock")


def test_control_lock_path_two_agents_roots_diverge(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PSC_AGENTS_ROOT", str(tmp_path / "agents-a"))
    assert cli.main(["control", "lock-path"]) == 0
    first = capsys.readouterr().out.strip()

    monkeypatch.setenv("PSC_AGENTS_ROOT", str(tmp_path / "agents-b"))
    assert cli.main(["control", "lock-path"]) == 0
    second = capsys.readouterr().out.strip()

    assert first != second


def test_control_help_lists_lock_path(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["control", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "lock-path" in out


def test_umbrella_help_mentions_control_lock_path(capsys):
    assert cli.main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "control lock-path" in out
