from __future__ import annotations

import json

from pygame_haxima.data.runtime_sprite_probe import converted_runtime_sprite_keys
from pygame_haxima.data.sprite_profile import SpriteProfile


def test_converted_runtime_sprite_keys_collects_places_townsfolk_and_quest_icons(tmp_path) -> None:
    converted = tmp_path / "converted_data"
    places = converted / "places"
    quests = converted / "quests"
    places.mkdir(parents=True, exist_ok=True)
    quests.mkdir(parents=True, exist_ok=True)

    (places / "zone.place.json").write_text(
        json.dumps(
            {
                "places": [
                    {"id": "p_cloviskeep", "name": "Cloviskeep", "sprite": "s_castle"},
                    {"id": "p_gate", "name": "Portal Gate", "sprite": "s_town"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (converted / "townsfolk.runtime.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_file": "alchemist.scm",
                        "factories": [{"id": "mk-alchemist", "name": "Alchemist"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (quests / "quests-data.quests.json").write_text(
        json.dumps({"quests": [{"id": "questentry-test", "icon": "s_enchanter"}]}),
        encoding="utf-8",
    )

    profile = SpriteProfile(frozenset({"alchemist", "portal"}))
    keys = converted_runtime_sprite_keys(converted, profile)

    assert "s_castle" in keys
    assert "s_town" in keys
    assert "s_enchanter" in keys
    assert "s_old_townsman" in keys
    # Derived object sprite from place content probe.
    assert "s_moongate_full" in keys
