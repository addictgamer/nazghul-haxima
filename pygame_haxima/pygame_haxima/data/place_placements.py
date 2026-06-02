from __future__ import annotations

from pygame_haxima.data.sprite_profile import SpriteProfile
from pygame_haxima.domain.models import Entity, Lever, Place, PlaceEntrance


def _bridge_blocked_tiles(x: int, y: int, direction: str) -> set[tuple[int, int]]:
    token = direction.strip().lower()
    if token in {"north", "n"}:
        return {(x, y - 1)}
    if token in {"south", "s"}:
        return {(x, y + 1)}
    if token in {"east", "e"}:
        return {(x + 1, y)}
    if token in {"west", "w"}:
        return {(x - 1, y)}
    return {(x, y - 1)}


def _species_stats(species: str) -> tuple[str, int, int, int, int]:
    normalized = species.strip().lower()
    if normalized == "wyrm":
        return ("Wyrm", 28, 4, 3, "s_wyrm_head")
    if normalized == "wolf":
        return ("Wolf", 10, 3, 1, "s_wolf")
    return (species.title(), 12, 3, 1, "s_wolf")


def apply_place_placements(
    place: Place,
    meta: dict,
    sprite_profile: SpriteProfile,
) -> None:
    placements = meta.get("placements")
    if not isinstance(placements, list):
        return

    for index, entry in enumerate(placements):
        if not isinstance(entry, dict):
            continue
        kind = entry.get("kind")
        x = entry.get("x")
        y = entry.get("y")
        if not isinstance(kind, str) or not isinstance(x, int) or not isinstance(y, int):
            continue
        if not place.in_bounds(x, y):
            continue

        if kind == "monster_spawn":
            species = entry.get("species")
            species_name = species if isinstance(species, str) else "monster"
            name, hp, attack, defense, default_sprite = _species_stats(species_name)
            entity_id = f"{species_name}_{index}"
            place.monsters.append(
                Entity(
                    entity_id=entity_id,
                    name=name,
                    x=x,
                    y=y,
                    sprite_key=sprite_profile.monster_sprite(entity_id, name, default_sprite),
                    hostile=True,
                    hp=hp,
                    max_hp=hp,
                    attack=attack,
                    defense=defense,
                )
            )
            continue

        if kind == "lever":
            bridge_id = entry.get("bridge_id")
            lever_id = f"lever_{bridge_id}" if isinstance(bridge_id, str) else f"lever_{index}"
            place.levers.append(
                Lever(
                    lever_id=lever_id,
                    bridge_id=str(bridge_id) if isinstance(bridge_id, str) else lever_id,
                    x=x,
                    y=y,
                )
            )
            continue

        if kind == "drawbridge":
            direction = entry.get("direction")
            direction_name = direction if isinstance(direction, str) else "north"
            bridge_id = entry.get("bridge_id")
            gate_id = bridge_id if isinstance(bridge_id, str) else f"bridge_{x}_{y}"
            tiles = _bridge_blocked_tiles(x, y, direction_name)
            place.bridge_blocked[gate_id] = set(tiles)
            place.blocked_tiles.update(tiles)
            continue

        if kind in {"monman", "tagged", "unknown"}:
            continue

    entrances = meta.get("entrances")
    if isinstance(entrances, list):
        for entry in entrances:
            if not isinstance(entry, dict):
                continue
            dest = entry.get("dest_place")
            ex = entry.get("x")
            ey = entry.get("y")
            if isinstance(dest, str) and isinstance(ex, int) and isinstance(ey, int):
                place.entrances.append(PlaceEntrance(dest_place=dest, x=ex, y=ey))


def place_key_from_id(place_id: str) -> str:
    normalized = place_id.strip().lower()
    if normalized in {"tutorial_wilderness", "tutorial"}:
        return "tutorial"
    if normalized in {"p_cloviskeep", "cloviskeep"}:
        return "cloviskeep"
    return normalized.removeprefix("p_")
