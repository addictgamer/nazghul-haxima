from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpellDef:
    spell_id: str
    name: str
    targeted: bool
    range_tiles: int
    reagents: dict[str, int]


SPELLS: dict[str, SpellDef] = {
    "spark": SpellDef(
        spell_id="spark",
        name="Spark",
        targeted=True,
        range_tiles=2,
        reagents={"sulphurous_ash": 1},
    ),
    "heal": SpellDef(
        spell_id="heal",
        name="Heal",
        targeted=False,
        range_tiles=0,
        reagents={"ginseng": 1},
    ),
    "ward": SpellDef(
        spell_id="ward",
        name="Ward",
        targeted=False,
        range_tiles=0,
        reagents={"garlic": 1},
    ),
}


def get_spell(spell_id: str) -> SpellDef | None:
    return SPELLS.get(spell_id)
