from __future__ import annotations

import pytest

from paulsha_cortex.deck.schema import (
    BAND_LEVELS,
    BandTriggeredSpine,
    DeckSchemaError,
    load_cards,
    load_combo,
)

# #221：gate_spine 兩層制（必要核心 + band 觸發加掛層）schema 支援。
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


def test_band_levels_order():
    assert BAND_LEVELS == ("green", "yellow", "red")


def test_load_combo_band_triggered_valid(tmp_path):
    cards, combo = _load(tmp_path, COMBO_WITH_BAND)
    # 核心層完全不含加掛卡：acceptance_surfaces 只讀這裡才不會誤把加掛層算進去
    assert [c.ref for c in combo.cards] == ["writing-plans", "code-review", "ship"]
    assert [gate.after for gate in combo.gate_spine] == ["writing-plans"]

    assert isinstance(combo.band_triggered, BandTriggeredSpine)
    assert combo.band_triggered.trigger == "yellow"
    assert [c.ref for c in combo.band_triggered.cards] == ["adversarial-review"]
    assert combo.band_triggered.cards[0].depends_on == ("code-review",)
    assert [(g.after, g.exists) for g in combo.band_triggered.gate_spine] == [
        ("adversarial-review", ("reports/review/*<task-slug>*-adversarial.md",)),
    ]


def test_load_combo_without_band_triggered_defaults_none(tmp_path):
    _, combo = _load(tmp_path, COMBO_WITHOUT_BAND)
    assert combo.band_triggered is None


def test_load_combo_band_triggered_unknown_key_rejected(tmp_path):
    bad = COMBO_WITH_BAND.replace("trigger: yellow", "trger: yellow")
    cards = load_cards(_write(tmp_path, "cards.yaml", CARDS_YAML))
    with pytest.raises(DeckSchemaError, match="trger"):
        load_combo(_write(tmp_path, "demo.yaml", bad), cards)


def test_load_combo_band_triggered_invalid_trigger_rejected(tmp_path):
    bad = COMBO_WITH_BAND.replace("trigger: yellow", "trigger: purple")
    cards = load_cards(_write(tmp_path, "cards.yaml", CARDS_YAML))
    with pytest.raises(DeckSchemaError, match="trigger 非法值"):
        load_combo(_write(tmp_path, "demo.yaml", bad), cards)


def test_load_combo_band_triggered_unknown_card_ref_rejected(tmp_path):
    bad = COMBO_WITH_BAND.replace("ref: adversarial-review", "ref: no-such-card")
    cards = load_cards(_write(tmp_path, "cards.yaml", CARDS_YAML))
    with pytest.raises(DeckSchemaError, match="no-such-card"):
        load_combo(_write(tmp_path, "demo.yaml", bad), cards)


def test_load_combo_band_triggered_duplicate_with_core_rejected(tmp_path):
    bad = COMBO_WITH_BAND.replace(
        "      - ref: adversarial-review\n        depends_on: [code-review]",
        "      - ref: code-review",
    )
    cards = load_cards(_write(tmp_path, "cards.yaml", CARDS_YAML))
    with pytest.raises(DeckSchemaError, match="band_triggered 卡片與骨幹重複"):
        load_combo(_write(tmp_path, "demo.yaml", bad), cards)


def test_load_combo_band_triggered_gate_after_unknown_rejected(tmp_path):
    bad = COMBO_WITH_BAND.replace(
        "      - after: adversarial-review\n        exists:",
        "      - after: no-such-card\n        exists:",
    )
    cards = load_cards(_write(tmp_path, "cards.yaml", CARDS_YAML))
    with pytest.raises(DeckSchemaError, match="不存在卡片"):
        load_combo(_write(tmp_path, "demo.yaml", bad), cards)


def test_load_combo_band_triggered_gate_empty_exists_rejected(tmp_path):
    bad = COMBO_WITH_BAND.replace(
        'exists: ["reports/review/*<task-slug>*-adversarial.md"]',
        "exists: []",
    )
    cards = load_cards(_write(tmp_path, "cards.yaml", CARDS_YAML))
    with pytest.raises(DeckSchemaError, match="exists"):
        load_combo(_write(tmp_path, "demo.yaml", bad), cards)


def test_load_combo_band_triggered_depends_on_outside_combo_rejected(tmp_path):
    bad = COMBO_WITH_BAND.replace("depends_on: [code-review]", "depends_on: [no-such-dep]")
    cards = load_cards(_write(tmp_path, "cards.yaml", CARDS_YAML))
    with pytest.raises(DeckSchemaError, match="depends_on 指向 combo 外卡片"):
        load_combo(_write(tmp_path, "demo.yaml", bad), cards)


def test_load_combo_band_triggered_non_mapping_rejected(tmp_path):
    bad = COMBO_WITHOUT_BAND + "  band_triggered: [oops]\n"
    cards = load_cards(_write(tmp_path, "cards.yaml", CARDS_YAML))
    with pytest.raises(DeckSchemaError, match="band_triggered 必須是 mapping"):
        load_combo(_write(tmp_path, "demo.yaml", bad), cards)
