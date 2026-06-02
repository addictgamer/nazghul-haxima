from __future__ import annotations

import json
from pathlib import Path

from pygame_haxima.domain.models import Terrain


def _terrain_color(tag: str) -> tuple[int, int, int]:
    value = abs(hash(tag))
    return ((value >> 16) & 200) + 40, ((value >> 8) & 200) + 40, (value & 200) + 40


def _terrain_glyph(name: str) -> str:
    stripped = name.strip()
    if not stripped:
        return "?"
    return stripped[0]


def load_terrain_registry(converted_data_dir: Path) -> dict[str, Terrain]:
    path = converted_data_dir / "terrains.runtime.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    terrains: dict[str, Terrain] = {}
    for entry in payload.get("terrains", []):
        if not isinstance(entry, dict):
            continue
        tag = entry.get("tag")
        name = entry.get("name")
        if not isinstance(tag, str) or not isinstance(name, str):
            continue
        passable = bool(entry.get("passable", True))
        sprite = entry.get("sprite")
        sprite_key = sprite if isinstance(sprite, str) else None
        terrains[tag] = Terrain(
            terrain_id=tag,
            name=name,
            passable=passable,
            glyph=_terrain_glyph(name),
            color=_terrain_color(tag),
            sprite_key=sprite_key,
        )
    return terrains


def default_unknown_terrain(token: str) -> Terrain:
    return Terrain(
        terrain_id=f"unknown:{token}",
        name=f"Unknown ({token})",
        passable=False,
        glyph="?",
        color=(90, 90, 95),
        sprite_key=None,
    )
