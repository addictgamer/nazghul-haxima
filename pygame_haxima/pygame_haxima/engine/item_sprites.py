from __future__ import annotations

from pygame_haxima.domain.models import Item


def item_sprite_key(item: Item) -> str:
    if item.sprite_key:
        return item.sprite_key
    token = f"{item.item_id} {item.name}".lower()
    if "dagger" in token:
        return "s_dagger"
    if "armor" in token or "armour" in token:
        return "s_leather_armor"
    if "potion" in token:
        return "s_healing_potion"
    if "coin" in token or "gold" in token:
        return "s_gold_coins"
    return "s_gem"
