from pygame_haxima.data.content_registry import ContentRegistry
from pygame_haxima.engine.spells import get_spell, known_spell_ids


def test_known_spell_ids_include_tutorial_and_world_spells() -> None:
    known = known_spell_ids()
    assert "spark" in known
    assert "heal" in known
    assert "ward" in known
    assert "grav_por" in known


def test_world_spell_metadata_loads_reagents_and_targeting() -> None:
    spell = get_spell("grav_por")
    assert spell is not None
    assert spell.name.startswith("Magic Missile")
    assert spell.targeted is True
    assert spell.reagents.get("sulphurous_ash") == 1
    assert spell.reagents.get("black_pearl") == 1


def test_new_session_uses_data_driven_spellbook() -> None:
    session = ContentRegistry().make_new_session()
    assert "grav_por" in session.party.spells_known
    assert session.party.selected_spell == "spark"
