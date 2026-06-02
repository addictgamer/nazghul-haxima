from pathlib import Path

from pygame_haxima.data.place_loader import build_cloviskeep_slice, build_place_from_converted
from pygame_haxima.data.terrain_registry import load_terrain_registry


def test_load_cloviskeep_map_from_converted_data() -> None:
    root = Path(__file__).resolve().parents[1]
    converted = root / "converted_data"
    palettes = converted / "palettes.runtime.json"
    if not palettes.exists():
        from pygame_haxima.data.scm_converter import ScmConverter

        world = root.parent / "worlds" / "haxima-1.002"
        ScmConverter().convert_palette_file(world / "palette.scm", palettes)

    place = build_place_from_converted("p_cloviskeep", converted)
    assert place.place_id == "p_cloviskeep"
    assert place.width == 64
    assert place.height == 64
    assert len(place.tiles) == 64
    assert len(place.tiles[0]) == 64
    terrains = load_terrain_registry(converted)
    assert "t_cobblestone" in terrains or any("cobble" in tid for tid in place.terrain_defs)


def test_cloviskeep_slice_spawns_party_on_passable_tile() -> None:
    root = Path(__file__).resolve().parents[1]
    converted = root / "converted_data"
    palettes = converted / "palettes.runtime.json"
    if not palettes.exists():
        from pygame_haxima.data.scm_converter import ScmConverter

        world = root.parent / "worlds" / "haxima-1.002"
        ScmConverter().convert_palette_file(world / "palette.scm", palettes)

    place, party = build_cloviskeep_slice(converted)
    assert place.passable(party.x, party.y)
    assert len(place.npcs) == 1
    assert party.members[0].x == party.x
