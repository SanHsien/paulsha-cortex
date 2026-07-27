from __future__ import annotations

import pytest

from paulsha_cortex.deck.compile import DeckCompileError, compile_combo
from paulsha_cortex.deck.schema import load_cards, load_combo

# #221：compile_combo 的 band 兩層制行為（core vs band_triggered 加掛層）。
CARDS_YAML = """\
version: 0
cards:
  - id: writing-plans
    kind: skill
    type: interactive
    class: core
    skill_ref: "superpowers:writing-plans"
    requires: []
    produces: ["docs/superpowers/plans/*<task-slug>*.md"]
    persona_binding: planner
  - id: code-review
    kind: skill
    type: headless
    class: core
    skill_ref: "superpowers:requesting-code-review"
    requires: []
    produces: ["reports/review/*<task-slug>*.md"]
    persona_binding: reviewer
  - id: ship
    kind: skill
    type: headless
    class: core
    skill_ref: "conventional-commit"
    phase: ship
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
"""

COMBO_WITH_BAND = """\
combo:
  id: demo
  task_type: feature
  cards:
    - ref: writing-plans
    - ref: code-review
    - ref: ship
  gate_spine:
    - after: writing-plans
      exists: ["docs/superpowers/plans/*<task-slug>*.md"]
  band_triggered:
    trigger: yellow
    cards:
      - ref: adversarial-review
        depends_on: [code-review]
    gate_spine:
      - after: adversarial-review
        exists: ["reports/review/*<task-slug>*-adversarial.md"]
"""

COMBO_WITHOUT_BAND = """\
combo:
  id: demo
  task_type: feature
  cards:
    - ref: writing-plans
    - ref: code-review
    - ref: ship
  gate_spine:
    - after: writing-plans
      exists: ["docs/superpowers/plans/*<task-slug>*.md"]
"""


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _load(tmp_path, combo_text):
    cards = load_cards(_write(tmp_path, "cards.yaml", CARDS_YAML))
    return cards, load_combo(_write(tmp_path, "demo.yaml", combo_text), cards)


def test_band_default_none_conservatively_includes_band_layer(tmp_path):
    cards, combo = _load(tmp_path, COMBO_WITH_BAND)
    result = compile_combo(combo, cards, "demo task", change="demo")
    slug = result.task_slug
    assert [s.slice_id for s in result.slices] == [
        f"{slug}-code-review",
        f"{slug}-adversarial-review",
        f"{slug}-ship",
    ]
    assert result.core_gate_verify_commands == (
        f"cortex deck verify writing-plans --task-slug {slug}",
    )
    assert result.band_gate_verify_commands == (
        f"cortex deck verify adversarial-review --task-slug {slug}",
    )
    assert f"cortex deck verify adversarial-review --task-slug {slug}" in result.verify_commands


def test_band_below_trigger_excludes_band_layer(tmp_path):
    cards, combo = _load(tmp_path, COMBO_WITH_BAND)
    result = compile_combo(combo, cards, "demo task", change="demo", band="green")
    slug = result.task_slug
    assert [s.slice_id for s in result.slices] == [f"{slug}-code-review", f"{slug}-ship"]
    assert result.band_gate_verify_commands == ()
    assert not any("adversarial-review" in command for command in result.verify_commands)


@pytest.mark.parametrize("band", ["yellow", "red"])
def test_band_at_or_above_trigger_includes_band_layer(tmp_path, band):
    cards, combo = _load(tmp_path, COMBO_WITH_BAND)
    result = compile_combo(combo, cards, "demo task", change="demo", band=band)
    slug = result.task_slug
    assert f"{slug}-adversarial-review" in [s.slice_id for s in result.slices]
    assert result.band_gate_verify_commands


def test_band_invalid_value_rejected(tmp_path):
    cards, combo = _load(tmp_path, COMBO_WITH_BAND)
    with pytest.raises(DeckCompileError, match="band 非法值"):
        compile_combo(combo, cards, "demo task", change="demo", band="purple")


def test_only_mode_skips_band_layer_even_with_default_band(tmp_path):
    cards, combo = _load(tmp_path, COMBO_WITH_BAND)
    result = compile_combo(
        combo, cards, "demo task", change="demo", only=("code-review",), allow_external=True
    )
    assert [s.slice_id for s in result.slices] == [f"{result.task_slug}-code-review"]
    assert result.band_gate_verify_commands == ()


def test_combo_without_band_triggered_is_noop_for_band_param(tmp_path):
    cards, combo = _load(tmp_path, COMBO_WITHOUT_BAND)
    result = compile_combo(combo, cards, "demo task", change="demo", band="red")
    assert [s.slice_id for s in result.slices] == [f"{result.task_slug}-code-review", f"{result.task_slug}-ship"]
    assert result.band_gate_verify_commands == ()


def test_band_card_inserted_after_its_dependency_not_at_tail(tmp_path):
    # 對抗回歸：加掛卡若只是無條件附加到 hand 尾端，會跑到 ship 之後，
    # 破壞既有「review 先於 ship」語意——必須依 depends_on 插到正確位置。
    cards, combo = _load(tmp_path, COMBO_WITH_BAND)
    result = compile_combo(combo, cards, "demo task", change="demo", band="yellow")
    slice_ids = [s.slice_id for s in result.slices]
    assert slice_ids.index(f"{result.task_slug}-adversarial-review") < slice_ids.index(f"{result.task_slug}-ship")
