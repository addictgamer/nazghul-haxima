from __future__ import annotations

import json
from pathlib import Path

from pygame_haxima.data.sprite_profile import SpriteProfile


def converted_runtime_sprite_keys(converted_data_dir: Path, profile: SpriteProfile) -> set[str]:
    keys: set[str] = set()
    _collect_place_keys(converted_data_dir / "places", profile, keys)
    _collect_townsfolk_keys(converted_data_dir / "townsfolk.runtime.json", profile, keys)
    _collect_quest_icon_keys(converted_data_dir / "quests", keys)
    return {key for key in keys if key}


def _collect_place_keys(places_dir: Path, profile: SpriteProfile, out: set[str]) -> None:
    if not places_dir.exists():
        return
    for path in sorted(places_dir.glob("*.place.json")):
        payload = _read_json(path)
        if not isinstance(payload, dict):
            continue
        for place in payload.get("places", []):
            if not isinstance(place, dict):
                continue
            place_id = place.get("id", "")
            name = place.get("name", "")
            sprite = place.get("sprite")
            if isinstance(sprite, str):
                out.add(sprite)
            if isinstance(place_id, str) and isinstance(name, str):
                out.add(profile.object_sprite(place_id, name, "s_chest"))


def _collect_townsfolk_keys(path: Path, profile: SpriteProfile, out: set[str]) -> None:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return
    for entry in payload.get("entries", []):
        if not isinstance(entry, dict):
            continue
        source_file = entry.get("source_file", "")
        for factory in entry.get("factories", []):
            if not isinstance(factory, dict):
                continue
            factory_id = factory.get("id", "")
            name = factory.get("name", "")
            if isinstance(factory_id, str) and isinstance(name, str):
                out.add(profile.npc_sprite(factory_id, name, "s_old_townsman"))
            if isinstance(factory_id, str):
                out.add(profile.npc_sprite(factory_id, str(source_file), "s_old_townsman"))


def _collect_quest_icon_keys(quests_dir: Path, out: set[str]) -> None:
    if not quests_dir.exists():
        return
    for path in sorted(quests_dir.glob("*.quests.json")):
        payload = _read_json(path)
        if not isinstance(payload, dict):
            continue
        for quest in payload.get("quests", []):
            if not isinstance(quest, dict):
                continue
            icon = quest.get("icon")
            if isinstance(icon, str):
                out.add(icon)


def _read_json(path: Path) -> object:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
