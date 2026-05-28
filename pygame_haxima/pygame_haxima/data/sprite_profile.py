from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

WORD_RE = re.compile(r"[A-Za-z0-9]+")

NPC_TOKEN_SPRITES = {
    "mentor": "s_old_townsman",
    "townsman": "s_old_townsman",
    "alchemist": "s_old_townsman",
    "lord": "s_lord",
}

MONSTER_TOKEN_SPRITES = {
    "wolf": "s_wolf",
    "snake": "s_snake",
    "spider": "s_spider",
    "rat": "s_rat",
    "bat": "s_bat",
    "orc": "s_orc",
}

OBJECT_TOKEN_SPRITES = {
    "chest": "s_chest",
    "door": "s_door",
    "portal": "s_moongate_full",
}


@dataclass(frozen=True)
class SpriteProfile:
    known_terms: frozenset[str]

    def player_sprite(self, fallback: str = "s_wanderer") -> str:
        return fallback

    def npc_sprite(self, entity_id: str, name: str, fallback: str = "s_old_townsman") -> str:
        return self._resolve(entity_id, name, NPC_TOKEN_SPRITES, fallback)

    def monster_sprite(self, entity_id: str, name: str, fallback: str = "s_wolf") -> str:
        return self._resolve(entity_id, name, MONSTER_TOKEN_SPRITES, fallback)

    def object_sprite(self, object_id: str, label: str, fallback: str = "s_chest") -> str:
        return self._resolve(object_id, label, OBJECT_TOKEN_SPRITES, fallback)

    def _resolve(self, identifier: str, label: str, token_map: dict[str, str], fallback: str) -> str:
        tokens = _tokenize(f"{identifier} {label}")
        for token in tokens:
            sprite = token_map.get(token)
            if sprite is None:
                continue
            if token in self.known_terms:
                return sprite
        return fallback


def load_sprite_profile(converted_data_dir: Path) -> SpriteProfile:
    terms: set[str] = set()
    _load_townsfolk_terms(converted_data_dir / "townsfolk.runtime.json", terms)
    _load_place_terms(converted_data_dir / "places", terms)
    return SpriteProfile(known_terms=frozenset(terms))


def _load_townsfolk_terms(path: Path, out: set[str]) -> None:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return
    for item in payload.get("loaded_files", []):
        if isinstance(item, str):
            out.update(_tokenize(item))
    for entry in payload.get("entries", []):
        if not isinstance(entry, dict):
            continue
        source_file = entry.get("source_file")
        if isinstance(source_file, str):
            out.update(_tokenize(source_file))
        for convo in entry.get("conversations", []):
            if not isinstance(convo, dict):
                continue
            convo_id = convo.get("id")
            if isinstance(convo_id, str):
                out.update(_tokenize(convo_id))
            for keyword in convo.get("keywords", []):
                if isinstance(keyword, str):
                    out.update(_tokenize(keyword))
        for factory in entry.get("factories", []):
            if not isinstance(factory, dict):
                continue
            for key in ("id", "name", "builder"):
                value = factory.get(key)
                if isinstance(value, str):
                    out.update(_tokenize(value))
            for ref in factory.get("references", []):
                if isinstance(ref, str):
                    out.update(_tokenize(ref))


def _load_place_terms(places_dir: Path, out: set[str]) -> None:
    if not places_dir.exists():
        return
    for path in sorted(places_dir.glob("*.place.json")):
        payload = _read_json(path)
        if not isinstance(payload, dict):
            continue
        for place in payload.get("places", []):
            if not isinstance(place, dict):
                continue
            for key in ("id", "name", "sprite", "source_file"):
                value = place.get(key)
                if isinstance(value, str):
                    out.update(_tokenize(value))
            for hook in place.get("on_entry_hooks", []):
                if isinstance(hook, str):
                    out.update(_tokenize(hook))


def _tokenize(text: str) -> set[str]:
    return {m.group(0).lower() for m in WORD_RE.finditer(text)}


def _read_json(path: Path) -> object:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
