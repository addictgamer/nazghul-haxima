from __future__ import annotations

import json
from pathlib import Path

from pygame_haxima.data.sprite_profile import SpriteProfile
from pygame_haxima.data.terrain_registry import default_unknown_terrain, load_terrain_registry
from pygame_haxima.data.tutorial_slice import build_tutorial_place
from pygame_haxima.domain.models import Entity, Npc, Party, Place, Tile


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_palette_tokens(converted_data_dir: Path, palette_id: str) -> dict[str, str]:
    path = converted_data_dir / "palettes.runtime.json"
    if not path.exists():
        return {}
    payload = _read_json(path)
    for palette in payload.get("palettes", []):
        if not isinstance(palette, dict):
            continue
        if palette.get("id") != palette_id:
            continue
        tokens = palette.get("tokens")
        if isinstance(tokens, dict):
            return {str(k): str(v) for k, v in tokens.items()}
    return {}


def _find_map_entry(converted_data_dir: Path, map_id: str) -> dict | None:
    maps_dir = converted_data_dir / "maps"
    for map_file in maps_dir.glob("*.map.json"):
        payload = _read_json(map_file)
        for entry in payload.get("maps", []):
            if isinstance(entry, dict) and entry.get("id") == map_id:
                return entry
    return None


def _find_place_meta(converted_data_dir: Path, place_id: str) -> dict | None:
    places_dir = converted_data_dir / "places"
    for place_file in places_dir.glob("*.place.json"):
        payload = _read_json(place_file)
        for entry in payload.get("places", []):
            if isinstance(entry, dict) and entry.get("id") == place_id:
                return entry
    return None


def _spell_context_for_place(meta: dict) -> str:
    if meta.get("wilderness"):
        return "context-world"
    if meta.get("underground"):
        return "context-town"
    return "context-town"


def _find_spawn_tile(place: Place, preferred: tuple[int, int] | None = None) -> tuple[int, int]:
    if preferred is not None:
        px, py = preferred
        if place.in_bounds(px, py) and place.passable(px, py):
            return px, py
    height, width = place.height, place.width
    for y in range(height // 4, height * 3 // 4):
        for x in range(width // 4, width * 3 // 4):
            if place.passable(x, y):
                return x, y
    return width // 2, height // 2


def build_place_from_converted(
    place_id: str,
    converted_data_dir: Path,
    sprite_profile: SpriteProfile | None = None,
) -> Place:
    meta = _find_place_meta(converted_data_dir, place_id)
    if meta is None:
        raise ValueError(f"Unknown converted place id: {place_id}")
    map_id = meta.get("map")
    if not isinstance(map_id, str):
        raise ValueError(f"Place {place_id} has no map reference")
    map_entry = _find_map_entry(converted_data_dir, map_id)
    if map_entry is None:
        raise ValueError(f"Map {map_id} not found for place {place_id}")

    palette_id = map_entry.get("palette", "pal_expanded")
    token_map = _load_palette_tokens(converted_data_dir, str(palette_id))
    terrain_registry = load_terrain_registry(converted_data_dir)
    unknown_cache: dict[str, Terrain] = {}

    width = int(map_entry["width"])
    height = int(map_entry["height"])
    tile_rows = map_entry.get("tile_rows")
    if not isinstance(tile_rows, list):
        raise ValueError(f"Map {map_id} is missing tile_rows")

    terrain_defs: dict[str, Terrain] = {}
    tiles: list[list[Tile]] = []
    for y in range(height):
        row_tokens = tile_rows[y] if y < len(tile_rows) else []
        row: list[Tile] = []
        for x in range(width):
            token = row_tokens[x] if x < len(row_tokens) else "xx"
            terrain_tag = token_map.get(token, "t_wall")
            terrain = terrain_registry.get(terrain_tag)
            if terrain is None:
                terrain = unknown_cache.get(terrain_tag)
                if terrain is None:
                    terrain = default_unknown_terrain(terrain_tag)
                    unknown_cache[terrain_tag] = terrain
            terrain_defs[terrain.terrain_id] = terrain
            row.append(Tile(terrain_id=terrain.terrain_id))
        tiles.append(row)

    hooks = meta.get("on_entry_hooks")
    hook_list = [hook for hook in hooks if isinstance(hook, str)] if isinstance(hooks, list) else []

    return Place(
        place_id=place_id,
        name=str(meta.get("name", place_id)),
        width=width,
        height=height,
        terrain_defs=terrain_defs,
        tiles=tiles,
        npcs=[],
        monsters=[],
        chests=[],
        spell_context=_spell_context_for_place(meta),
        on_entry_hooks=hook_list,
    )


def build_cloviskeep_slice(
    converted_data_dir: Path,
    sprite_profile: SpriteProfile | None = None,
) -> tuple[Place, Party]:
    profile = sprite_profile or SpriteProfile(frozenset())
    place = build_place_from_converted("p_cloviskeep", converted_data_dir, profile)
    spawn_x, spawn_y = _find_spawn_tile(place, preferred=(30, 28))

    party_lead = Entity(
        entity_id="wanderer",
        name="The Wanderer",
        x=spawn_x,
        y=spawn_y,
        sprite_key=profile.player_sprite("s_wanderer"),
        hp=20,
        max_hp=20,
        ap=50,
        attack=4,
        defense=2,
    )
    party = Party(x=spawn_x, y=spawn_y, members=[party_lead])

    guard = Npc(
        npc_id="clovis_guard",
        name="Keep Guard",
        x=min(spawn_x + 2, place.width - 2),
        y=spawn_y,
        sprite_key=profile.npc_sprite("clovis_guard", "Keep Guard", "s_lord"),
        keywords={
            "name": "I am a guard of Cloviskeep.",
            "job": "I watch the drawbridge and inner yard.",
            "quest": "The Enchanter sent word—seek him in the tower when you are ready.",
            "bye": "Walk in wisdom.",
        },
    )
    place.npcs.append(guard)
    return place, party


def build_place_by_key(
    place_key: str,
    converted_data_dir: Path,
    sprite_profile: SpriteProfile | None = None,
) -> tuple[Place, Party]:
    normalized = place_key.strip().lower()
    if normalized in {"tutorial", "tutorial_wilderness"}:
        return build_tutorial_place(sprite_profile)
    if normalized in {"cloviskeep", "p_cloviskeep"}:
        return build_cloviskeep_slice(converted_data_dir, sprite_profile)
    raise ValueError(f"Unsupported place key: {place_key}")
