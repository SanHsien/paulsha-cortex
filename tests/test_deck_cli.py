from __future__ import annotations

from pathlib import Path

import yaml

from paulsha_cortex.deck import cli as deck_cli

CARDS_YAML = """\
version: 0
cards:
  - id: brainstorming
    kind: skill
    type: interactive
    class: core
    skill_ref: "superpowers:brainstorming"
    requires: []
    produces: ["docs/superpowers/specs/*<task-slug>*-design.md"]
    persona_binding: planner
  - id: openspec-propose
    kind: skill
    type: interactive
    class: core
    skill_ref: "openspec-propose"
    requires: ["docs/superpowers/specs/*<task-slug>*-design.md"]
    produces:
      - "openspec/changes/<change>/proposal.md"
      - "openspec/changes/<change>/tasks.md"
    persona_binding: planner
  - id: writing-plans
    kind: skill
    type: interactive
    class: core
    skill_ref: "superpowers:writing-plans"
    requires: ["openspec/changes/<change>/proposal.md"]
    produces: ["docs/superpowers/plans/*<task-slug>*.md"]
    persona_binding: planner
  - id: worktree-isolation
    kind: skill
    type: headless
    class: core
    skill_ref: "superpowers:using-git-worktrees"
    slice_group: build
    requires: ["docs/superpowers/plans/*<task-slug>*.md"]
    produces: []
    persona_binding: builder
  - id: tdd-red
    kind: skill
    type: headless
    class: core
    skill_ref: "superpowers:test-driven-development"
    slice_group: build
    requires: []
    produces: []
    persona_binding: builder
  - id: subagent-build
    kind: skill
    type: headless
    class: core
    skill_ref: "superpowers:subagent-driven-development"
    slice_group: build
    requires: []
    produces: []
    persona_binding: builder
  - id: code-review
    kind: skill
    type: headless
    class: core
    skill_ref: "superpowers:requesting-code-review"
    requires: []
    produces: ["reports/review/*<task-slug>*.md"]
    persona_binding: reviewer
  - id: verification
    kind: skill
    type: headless
    class: core
    skill_ref: "superpowers:verification-before-completion"
    requires: []
    produces: ["reports/verify/*<task-slug>*.md"]
    persona_binding: reviewer
  - id: openspec-archive
    kind: skill
    type: headless
    class: core
    skill_ref: "openspec-archive-change"
    slice_group: ship
    requires: ["openspec/changes/<change>/tasks.md"]
    produces: ["openspec/changes/archive/*<change>*"]
    persona_binding: manager
  - id: policy-commit
    kind: skill
    type: headless
    class: core
    skill_ref: "conventional-commit"
    slice_group: ship
    requires: []
    produces: []
    persona_binding: manager
  - id: adversarial-review
    kind: skill
    type: headless
    class: core
    skill_ref: "codex:adversarial-review"
    requires: ["reports/review/*<task-slug>*.md"]
    produces: ["reports/review/*<task-slug>*-adversarial.md"]
    persona_binding: reviewer
  - id: mcu-hw-evidence
    kind: skill
    type: interactive
    class: niche
    skill_ref: "mcu-coding-skill"
    requires: []
    produces: ["docs/superpowers/specs/*<task-slug>*-hw-evidence.md"]
    persona_binding: planner
"""

FEATURE_ONESHOT_YAML = """\
combo:
  id: feature-oneshot
  task_type: feature
  cards:
    - ref: brainstorming
    - ref: openspec-propose
    - ref: writing-plans
    - ref: worktree-isolation
    - ref: tdd-red
    - ref: subagent-build
    - ref: code-review
    - ref: verification
    - ref: openspec-archive
    - ref: policy-commit
    - ref: adversarial-review
  gate_spine:
    - after: writing-plans
      exists: ["docs/superpowers/plans/*<task-slug>*.md"]
    - after: code-review
      exists: ["reports/review/*<task-slug>*.md"]
"""

MCU_FEATURE_YAML = """\
combo:
  id: mcu-feature
  task_type: mcu-feature
  cards:
    - ref: mcu-hw-evidence
    - ref: writing-plans
    - ref: worktree-isolation
    - ref: tdd-red
    - ref: subagent-build
    - ref: code-review
    - ref: verification
  gate_spine:
    - after: mcu-hw-evidence
      exists: ["docs/superpowers/specs/*<task-slug>*-hw-evidence.md"]
"""


def _seed_fixture(tmp_path: Path, monkeypatch):
    tmp_path.mkdir(parents=True, exist_ok=True)
    cards_path = tmp_path / "cards.yaml"
    combos_dir = tmp_path / "combos"
    cards_path.write_text(CARDS_YAML, encoding="utf-8")
    combos_dir.mkdir()
    (combos_dir / "feature-oneshot.yaml").write_text(FEATURE_ONESHOT_YAML, encoding="utf-8")
    (combos_dir / "mcu-feature.yaml").write_text(MCU_FEATURE_YAML, encoding="utf-8")
    monkeypatch.setattr(deck_cli, "DEFAULT_CARDS_PATH", cards_path)
    monkeypatch.setattr(deck_cli, "DEFAULT_COMBOS_DIR", combos_dir)
    return cards_path, combos_dir


def test_list_shows_combos(tmp_path, capsys, monkeypatch):
    _seed_fixture(tmp_path, monkeypatch)
    assert deck_cli.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "feature-oneshot" in out and "mcu-feature" in out
    assert "card: brainstorming" in out
    assert "card: mcu-hw-evidence" in out


def test_list_can_filter_one_combo_and_shows_only_its_members(tmp_path, capsys, monkeypatch):
    _seed_fixture(tmp_path, monkeypatch)
    assert deck_cli.main(["list", "mcu-feature"]) == 0
    out = capsys.readouterr().out
    assert "mcu-feature" in out
    assert "card: mcu-hw-evidence" in out
    assert "feature-oneshot" not in out
    assert "card: brainstorming" not in out


def test_compile_dry_run_writes_nothing(tmp_path, capsys, monkeypatch):
    _seed_fixture(tmp_path / "deck", monkeypatch)
    specs_root = tmp_path / "specs"
    specs_root.mkdir()
    monkeypatch.setenv("PSC_MANAGER_SPECS_DIR", str(specs_root))
    rc = deck_cli.main(["compile", "feature-oneshot", "--task", "demo task", "--change", "demo", "--allow-external"])
    assert rc == 0
    assert list(specs_root.iterdir()) == []
    assert "dispatch: hold" in capsys.readouterr().out


def test_compile_dry_run_without_change_still_loads_default_data(tmp_path, capsys, monkeypatch):
    _seed_fixture(tmp_path / "deck", monkeypatch)
    rc = deck_cli.main(["compile", "feature-oneshot", "--task", "demo task"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "task-slug: demo-task" in out
    assert "dispatch: hold" in out


def test_compile_emit_writes_hold_specs_and_reports_absolute_paths(tmp_path, capsys, monkeypatch):
    _seed_fixture(tmp_path / "deck", monkeypatch)
    specs_root = tmp_path / "specs"
    monkeypatch.setenv("PSC_MANAGER_SPECS_DIR", str(specs_root))
    rc = deck_cli.main(
        ["compile", "feature-oneshot", "--task", "demo task", "--change", "demo", "--allow-external", "--emit"]
    )
    assert rc == 0
    files = sorted(specs_root.glob("*.md"))
    assert files
    assert all("dispatch: hold" in path.read_text(encoding="utf-8") for path in files)
    captured = capsys.readouterr()
    assert f"output-dir: {specs_root.resolve()}" in captured.out
    assert all(str(path.resolve()) in captured.out for path in files)
    assert "--repo owner/repo" in captured.err


def test_compile_cjk_task_warns_and_explicit_slug_is_used(tmp_path, capsys, monkeypatch):
    _seed_fixture(tmp_path / "deck", monkeypatch)
    rc = deck_cli.main(
        [
            "compile",
            "feature-oneshot",
            "--task",
            "Task 5 - 建立共用測試",
            "--slug",
            "shared-test-helper",
            "--change",
            "demo",
            "--allow-external",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "task-slug: shared-test-helper" in captured.out
    assert "--slug" not in captured.err

    rc = deck_cli.main(
        [
            "compile",
            "feature-oneshot",
            "--task",
            "Task 5 - 建立共用測試",
            "--change",
            "demo",
            "--allow-external",
        ]
    )
    assert rc == 0
    assert "--slug" in capsys.readouterr().err


def test_compile_emit_carries_explicit_work_item_repo(tmp_path, monkeypatch):
    _seed_fixture(tmp_path / "deck", monkeypatch)
    specs_root = tmp_path / "specs"
    rc = deck_cli.main(
        [
            "compile",
            "feature-oneshot",
            "--task",
            "demo task",
            "--change",
            "demo",
            "--allow-external",
            "--repo",
            "hamanpaul/paulsha-cortex",
            "--out",
            str(specs_root),
        ]
    )

    assert rc == 0
    files = sorted(specs_root.glob("*.md"))
    assert files
    assert all(
        yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])["repo"]
        == "hamanpaul/paulsha-cortex"
        for path in files
    )


def test_compile_out_file_path_reports_error(tmp_path, capsys, monkeypatch):
    _seed_fixture(tmp_path / "deck", monkeypatch)
    out_file = tmp_path / "not-a-dir"
    out_file.write_text("occupied", encoding="utf-8")
    rc = deck_cli.main(
        [
            "compile",
            "feature-oneshot",
            "--task",
            "demo task",
            "--change",
            "demo",
            "--allow-external",
            "--out",
            str(out_file),
        ]
    )
    assert rc == 1
    assert "deck:" in capsys.readouterr().err


def test_verify_missing_change_returns_cli_error(tmp_path, capsys, monkeypatch):
    _seed_fixture(tmp_path / "deck", monkeypatch)
    rc = deck_cli.main(["verify", "openspec-archive", "--task-slug", "demo-task"])
    assert rc == 1
    assert "deck:" in capsys.readouterr().err
