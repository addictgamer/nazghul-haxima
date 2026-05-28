from pygame_haxima.domain.models import Item
from pygame_haxima.engine.item_sprites import item_sprite_key


def test_item_sprite_key_prefers_weapon_category_with_atlas_fallback() -> None:
    item = Item("t_longsword", "Long Sword", 35)
    available = {"s_dagger"}
    assert item_sprite_key(item, available.__contains__) == "s_dagger"


def test_item_sprite_key_maps_reagents_and_currency_categories() -> None:
    ash = Item("t_sulphorous_ash", "Sulphorous Ash", 5)
    gold = Item("t_gold_coins", "Gold Coins", 1)
    available = {"s_reagent", "s_gold_coins"}
    assert item_sprite_key(ash, available.__contains__) == "s_reagent"
    assert item_sprite_key(gold, available.__contains__) == "s_gold_coins"


def test_item_sprite_key_preserves_explicit_override() -> None:
    item = Item("t_unknown", "Unknown Curio", 2, sprite_key="s_custom_icon")
    assert item_sprite_key(item) == "s_custom_icon"
