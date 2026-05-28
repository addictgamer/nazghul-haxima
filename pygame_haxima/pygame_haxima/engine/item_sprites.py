from __future__ import annotations

from collections.abc import Callable
import re

from pygame_haxima.domain.models import Item

WORD_RE = re.compile(r"[a-z0-9]+")

CANONICAL_ITEM_SPRITES: dict[str, tuple[str, ...]] = {
    "weapon": ("s_sword", "s_dagger"),
    "armor": ("s_chain_armor", "s_leather_armor"),
    "shield": ("s_shield", "s_leather_armor"),
    "helm": ("s_helm", "s_leather_armor"),
    "boots": ("s_boots", "s_leather_armor"),
    "potion": ("s_healing_potion",),
    "scroll": ("s_scroll", "s_gem"),
    "ring": ("s_ring", "s_gem"),
    "amulet": ("s_ankh_amulet", "s_gem"),
    "food": ("s_ration", "s_gem"),
    "reagent": ("s_reagent", "s_gem"),
    "currency": ("s_gold_coins",),
    "default": ("s_gem",),
}

TOKEN_CATEGORY_HINTS: tuple[tuple[set[str], str], ...] = (
    ({"sword", "axe", "mace", "club", "spear", "staff", "bow", "crossbow", "dagger"}, "weapon"),
    ({"armor", "armour", "mail", "plate", "tunic", "cloak"}, "armor"),
    ({"shield", "buckler"}, "shield"),
    ({"helm", "helmet", "cap", "hood", "hat"}, "helm"),
    ({"boot", "boots", "greave", "greaves", "sandals", "shoe", "shoes"}, "boots"),
    ({"potion", "elixir", "philter", "tonic"}, "potion"),
    ({"scroll"}, "scroll"),
    ({"ring", "band"}, "ring"),
    ({"amulet", "talisman", "necklace", "pendant", "ankh"}, "amulet"),
    ({"bread", "meat", "fish", "cheese", "apple", "ration", "food"}, "food"),
    ({"ginseng", "garlic", "ash", "moss", "nightshade", "mandrake", "reagent"}, "reagent"),
    ({"coin", "coins", "gold"}, "currency"),
)

REAGENT_SPRITE_KEYS: dict[str, str] = {
    "sulphorous_ash": "s_sulphorous_ash",
    "sulphurous_ash": "s_sulphorous_ash",
    "ginseng": "s_ginseng",
    "garlic": "s_garlic",
    "nightshade": "s_nightshade",
    "mandrake": "s_mandrake",
    "blood_moss": "s_blood_moss",
    "black_pearl": "s_black_pearl",
    "spider_silk": "s_spider_silk",
}


def _tokenize(text: str) -> set[str]:
    return {match.group(0) for match in WORD_RE.finditer(text.lower())}


def _best_available(candidates: tuple[str, ...], has_sprite_key: Callable[[str], bool] | None) -> str:
    if has_sprite_key is None:
        return candidates[0]
    for key in candidates:
        if has_sprite_key(key):
            return key
    return candidates[-1]


def item_sprite_key(item: Item, has_sprite_key: Callable[[str], bool] | None = None) -> str:
    if item.sprite_key:
        return item.sprite_key
    raw_text = f"{item.item_id} {item.name}".lower()
    tokens = _tokenize(raw_text)
    for reagent_token, sprite_key in REAGENT_SPRITE_KEYS.items():
        if (
            (reagent_token in raw_text or set(reagent_token.split("_")).issubset(tokens))
            and (has_sprite_key is None or has_sprite_key(sprite_key))
        ):
            return sprite_key
    for hints, category in TOKEN_CATEGORY_HINTS:
        if tokens.intersection(hints):
            return _best_available(CANONICAL_ITEM_SPRITES[category], has_sprite_key)
    return _best_available(CANONICAL_ITEM_SPRITES["default"], has_sprite_key)
