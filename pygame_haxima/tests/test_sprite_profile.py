from __future__ import annotations

import json

from pygame_haxima.data.sprite_profile import SpriteProfile, load_sprite_profile
from pygame_haxima.data.tutorial_slice import build_tutorial_place


def test_load_sprite_profile_collects_terms_from_converted_outputs(tmp_path) -> None:
    converted = tmp_path / "converted_data"
    places = converted / "places"
    places.mkdir(parents=True, exist_ok=True)
    (converted / "townsfolk.runtime.json").write_text(
        json.dumps(
            {
                "loaded_files": ["townsfolk/wolfmaster.scm"],
                "entries": [
                    {
                        "source_file": "wolfmaster.scm",
                        "conversations": [{"id": "wolfmaster-conv", "keywords": ["wolf", "name"]}],
                        "factories": [{"id": "mk-wolfmaster", "builder": "mk-townsman", "references": []}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (places / "demo.place.json").write_text(
        json.dumps(
            {
                "places": [
                    {
                        "id": "p_demo",
                        "name": "Wolf Den",
                        "sprite": "s_castle",
                        "on_entry_hooks": ["on-entry-wolf"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    profile = load_sprite_profile(converted)

    assert "wolf" in profile.known_terms
    assert "townsman" in profile.known_terms
    assert profile.monster_sprite("wolf_1", "Wolf", "s_rat") == "s_wolf"


def test_build_tutorial_place_uses_profile_for_runtime_sprite_keys() -> None:
    profile = SpriteProfile(frozenset({"mentor", "wolf", "chest"}))
    place, party = build_tutorial_place(profile)

    assert party.members[0].sprite_key == "s_wanderer"
    assert place.npcs[0].sprite_key == "s_old_townsman"
    assert place.monsters[0].sprite_key == "s_wolf"
    assert place.chests[0].sprite_key == "s_chest"
