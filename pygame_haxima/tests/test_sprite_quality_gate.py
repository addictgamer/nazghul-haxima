from __future__ import annotations

from pathlib import Path

import pygame

from pygame_haxima.data.asset_loader import AssetLoader
from pygame_haxima.data.sprite_atlas import SpriteAtlas


def test_critical_sprite_keys_are_not_fallbacks() -> None:
    pygame.init()
    project_root = Path(__file__).resolve().parents[1]
    atlas = SpriteAtlas(asset_loader=AssetLoader(project_root), project_root=project_root)
    atlas.load()

    critical_keys = {
        # player / npc / monster
        "s_wanderer",
        "s_old_townsman",
        "s_wolf",
        # terrain (Cloviskeep dirt uses ss_addon index 137)
        "s_dirt",
        # object categories
        "s_chest",
        "s_door",
        # item categories
        "s_dagger",
        "s_leather_armor",
        "s_healing_potion",
        "s_gold_coins",
        "s_gem",
    }
    fallback_keys = sorted(key for key in critical_keys if atlas.is_fallback(key))
    pygame.quit()

    assert not fallback_keys, f"Critical sprite fallbacks detected: {', '.join(fallback_keys)}"
