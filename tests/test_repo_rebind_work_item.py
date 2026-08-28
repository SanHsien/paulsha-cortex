from pathlib import Path
import os
import subprocess
import pytest

from paulsha_cortex.monitor.config import load_config, _resolve_config_source
from paulsha_cortex.coordinator.work_actions import execute_work_action
from paulsha_cortex.doctor import run_doctor


def test_legacy_config_fallback_fails_loudly(monkeypatch, tmp_path):
    """Finding 1: Legacy config file fallback must fail loudly, not silently succeed."""
    monkeypatch.delenv("PSC_MONITOR_CONFIG", raising=False)
    monkeypatch.delenv("PAULSHACLAW_CONFIG", raising=False)
    monkeypatch.setenv("PSC_PROJECT_CONFIG_ROOT", str(tmp_path / "agents"))
    monkeypatch.setenv("PSC_CONFIG_ROOT", str(tmp_path / "legacy"))
    
    # Create legacy file only
    legacy_file = tmp_path / "legacy" / "paulshaclaw.yaml"
    legacy_file.parent.mkdir(parents=True, exist_ok=True)
    legacy_file.write_text("workspaces:\n  - {name: old, path: /tmp/old}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="deprecated legacy monitor"):
        load_config()


def test_legacy_config_env_fails_loudly(monkeypatch, tmp_path):
    """Finding 1: Deprecated PAULSHACLAW_CONFIG env var must fail loudly."""
    legacy_file = tmp_path / "legacy" / "paulshaclaw.yaml"
    legacy_file.parent.mkdir(parents=True, exist_ok=True)
    legacy_file.write_text("workspaces:\n  - {name: old, path: /tmp/old}\n", encoding="utf-8")

    monkeypatch.setenv("PAULSHACLAW_CONFIG", str(legacy_file))
    monkeypatch.delenv("PSC_MONITOR_CONFIG", raising=False)
    monkeypatch.setenv("PSC_PROJECT_CONFIG_ROOT", str(tmp_path / "agents"))

    with pytest.raises(ValueError, match="PAULSHACLAW_CONFIG"):
        load_config()


def test_monitor_config_includes_psc_repo_root(monkeypatch, tmp_path):
    """Finding 1: Monitor config resolution must include PSC_REPO_ROOT as a monitored project."""
    repo_b = tmp_path / "repoB"
    repo_b.mkdir(parents=True)
    (repo_b / ".cortex").mkdir()
    (repo_b / ".cortex" / "work-items.yaml").write_text(
        "version: 1\nwork_items:\n  item-b:\n    title: Item B\n    links: []\n    excludes: []\n",
        encoding="utf-8"
    )
    
    monkeypatch.setenv("PSC_REPO_ROOT", str(repo_b))
    monkeypatch.setenv("PSC_PROJECT_CONFIG_ROOT", str(tmp_path / "agents"))
    
    config = load_config()
    project_paths = [p.path for p in config.hippo_projects] + [w.path for w in config.workspaces]
    assert repo_b.resolve() in [p.resolve() for p in project_paths]


def test_doctor_fails_when_legacy_config_used(monkeypatch, tmp_path):
    """Finding 1: Doctor probe must fail when legacy config is present/used."""
    monkeypatch.delenv("PSC_MONITOR_CONFIG", raising=False)
    monkeypatch.delenv("PAULSHACLAW_CONFIG", raising=False)
    monkeypatch.setenv("PSC_PROJECT_CONFIG_ROOT", str(tmp_path / "agents"))
    monkeypatch.setenv("PSC_CONFIG_ROOT", str(tmp_path / "legacy"))
    
    legacy_file = tmp_path / "legacy" / "paulshaclaw.yaml"
    legacy_file.parent.mkdir(parents=True, exist_ok=True)
    legacy_file.write_text("workspaces:\n  - {name: old, path: /tmp/old}\n", encoding="utf-8")

    report = run_doctor(probe_live=False, env=os.environ, home=tmp_path)
    assert not report.ok
    assert any(p.name == "monitor-socket" and p.status == "fail" for p in report.probes)


def test_work_link_preserves_yaml_key_ordering(tmp_path):
    """Finding 2: work link must preserve key ordering in work-items.yaml."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:owner/repo.git"], cwd=repo, check=True, capture_output=True)

    cortex_dir = repo / ".cortex"
    cortex_dir.mkdir(parents=True)
    yaml_file = cortex_dir / "work-items.yaml"
    
    # Write keys in non-alphabetical order
    yaml_content = (
        "version: 1\n"
        "work_items:\n"
        "  zebra-task:\n"
        "    title: Zebra\n"
        "    links: []\n"
        "    excludes: []\n"
        "  alpha-task:\n"
        "    title: Alpha\n"
        "    links: []\n"
        "    excludes: []\n"
    )
    yaml_file.write_text(yaml_content, encoding="utf-8")

    args = {
        "action": "link",
        "repo": "owner/repo",
        "work_id": "alpha-task",
        "kind": "github_issue",
        "ref": "owner/repo#123",
        "repo_root": str(repo),
    }

    result = execute_work_action(args=args, requested_by="operator")
    
    updated_content = yaml_file.read_text(encoding="utf-8")
    zebra_pos = updated_content.find("zebra-task:")
    alpha_pos = updated_content.find("alpha-task:")
    assert zebra_pos != -1 and alpha_pos != -1
    assert zebra_pos < alpha_pos, "zebra-task must remain before alpha-task (key order preserved)"
