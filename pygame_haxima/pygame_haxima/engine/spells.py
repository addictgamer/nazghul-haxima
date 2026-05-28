from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pygame_haxima.data.scm_parser import Expr, ScmParser, Symbol


@dataclass(frozen=True)
class SpellDef:
    spell_id: str
    name: str
    targeted: bool
    range_tiles: int
    reagents: dict[str, int]
    circle: int = 1
    context: str = "context-any"
    icon_sprite: str | None = None
    effect_kind: str = "utility"


_SPELLS_CACHE: dict[str, SpellDef] | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _symbol_name(expr: Expr) -> str | None:
    if isinstance(expr, Symbol):
        return expr.name
    if isinstance(expr, list) and len(expr) == 2 and _symbol_name(expr[0]) == "quote":
        quoted = expr[1]
        if isinstance(quoted, Symbol):
            return quoted.name
    return None


def _spell_profile(spell_id: str, name: str, circle: int) -> tuple[str, bool, int]:
    token = f"{spell_id} {name}".lower()
    if spell_id == "spark":
        return "attack", True, 2
    if spell_id == "heal" or "heal" in token:
        return "heal", False, 0
    if spell_id == "ward" or "ward" in token or "protection" in token:
        return "ward", False, 0
    attack_terms = (
        "bolt",
        "ball",
        "spray",
        "missile",
        "fire",
        "flame",
        "poison",
        "lightning",
        "death",
        "tremor",
    )
    if any(term in token for term in attack_terms):
        return "attack", True, max(2, min(8, circle + 1))
    return "utility", False, 0


def _normalize_reagent(reagent_id: str) -> str:
    if reagent_id == "sulphorous_ash":
        return "sulphurous_ash"
    return reagent_id


def _parse_spells_from_world(path: Path) -> list[SpellDef]:
    if not path.exists():
        return []
    parser = ScmParser()
    exprs = parser.parse_text(path.read_text(encoding="utf-8", errors="ignore"))
    parsed: list[SpellDef] = []

    def visit(node: Expr) -> None:
        if not isinstance(node, list) or not node:
            return
        if _symbol_name(node[0]) == "mk-spell" and len(node) >= 9:
            spell_id = _symbol_name(node[1])
            name = node[2] if isinstance(node[2], str) else None
            circle = int(node[5]) if isinstance(node[5], int) else 1
            context = _symbol_name(node[6]) or "context-any"
            icon = _symbol_name(node[7])
            reagents_expr = node[8]
            reagents: dict[str, int] = {}
            if isinstance(reagents_expr, list) and reagents_expr and _symbol_name(reagents_expr[0]) == "list":
                for reagent_expr in reagents_expr[1:]:
                    reagent = _symbol_name(reagent_expr)
                    if reagent:
                        reagents[_normalize_reagent(reagent)] = reagents.get(
                            _normalize_reagent(reagent), 0
                        ) + 1
            if spell_id and name:
                effect_kind, targeted, range_tiles = _spell_profile(spell_id, name, circle)
                parsed.append(
                    SpellDef(
                        spell_id=spell_id,
                        name=name,
                        targeted=targeted,
                        range_tiles=range_tiles,
                        reagents=reagents,
                        circle=max(1, circle),
                        context=context,
                        icon_sprite=icon,
                        effect_kind=effect_kind,
                    )
                )
        for part in node:
            visit(part)

    for expr in exprs:
        visit(expr)
    return parsed


def _build_spell_registry() -> dict[str, SpellDef]:
    # Keep tutorial-friendly aliases while source-complete spell data loads from spells.scm.
    registry: dict[str, SpellDef] = {
        "spark": SpellDef(
            spell_id="spark",
            name="Spark",
            targeted=True,
            range_tiles=2,
            reagents={"sulphurous_ash": 1},
            circle=1,
            effect_kind="attack",
        ),
        "heal": SpellDef(
            spell_id="heal",
            name="Heal",
            targeted=False,
            range_tiles=0,
            reagents={"ginseng": 1},
            circle=1,
            effect_kind="heal",
        ),
        "ward": SpellDef(
            spell_id="ward",
            name="Ward",
            targeted=False,
            range_tiles=0,
            reagents={"garlic": 1},
            circle=1,
            effect_kind="ward",
        ),
    }
    world_spells = _parse_spells_from_world(_repo_root() / "worlds" / "haxima-1.002" / "spells.scm")
    for spell in world_spells:
        registry.setdefault(spell.spell_id, spell)
    return registry


def get_spell(spell_id: str) -> SpellDef | None:
    global _SPELLS_CACHE
    if _SPELLS_CACHE is None:
        _SPELLS_CACHE = _build_spell_registry()
    return _SPELLS_CACHE.get(spell_id)


def known_spell_ids() -> list[str]:
    global _SPELLS_CACHE
    if _SPELLS_CACHE is None:
        _SPELLS_CACHE = _build_spell_registry()
    return list(_SPELLS_CACHE.keys())
