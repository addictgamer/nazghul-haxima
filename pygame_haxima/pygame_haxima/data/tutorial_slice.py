from __future__ import annotations

from pygame_haxima.domain.models import Chest, Entity, Item, Npc, Party, Place, Terrain, Tile


def _make_tiles(width: int, height: int) -> list[list[Tile]]:
    rows: list[list[Tile]] = []
    for y in range(height):
        row: list[Tile] = []
        for x in range(width):
            terrain = "grass"
            if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                terrain = "wall"
            if y == 9 and 3 <= x <= 12:
                terrain = "road"
            row.append(Tile(terrain_id=terrain))
        rows.append(row)
    return rows


def build_tutorial_place() -> tuple[Place, Party]:
    terrain_defs = {
        "grass": Terrain(
            "grass",
            "Grass",
            passable=True,
            glyph=".",
            color=(80, 130, 70),
            sprite_key="s_grass",
        ),
        "road": Terrain(
            "road",
            "Road",
            passable=True,
            glyph="=",
            color=(130, 105, 70),
            sprite_key="s_cobblestone",
        ),
        "wall": Terrain(
            "wall",
            "Wall",
            passable=False,
            glyph="#",
            color=(70, 70, 75),
            sprite_key="s_wall",
        ),
    }
    width, height = 24, 18
    tiles = _make_tiles(width, height)

    party_lead = Entity(
        entity_id="wanderer",
        name="The Wanderer",
        x=3,
        y=9,
        sprite_key="s_party",
        hp=20,
        max_hp=20,
        ap=50,
        attack=4,
        defense=2,
    )
    party = Party(x=3, y=9, members=[party_lead])

    npc = Npc(
        npc_id="mentor",
        name="Old Mentor",
        x=7,
        y=9,
        sprite_key="s_npc",
        keywords={
            "name": "I am called the Old Mentor.",
            "job": "I teach wanderers how to survive Nazghul.",
            "chest": "To the south lies a chest with useful supplies.",
            "bye": "Walk in wisdom.",
        },
    )
    chest = Chest(
        chest_id="starter_chest",
        x=5,
        y=11,
        items=[
            Item("dagger", "Dagger", 8),
            Item("leather_armor", "Leather Armor", 12),
            Item("red_potion", "Red Potion", 15),
        ],
    )
    wolf = Entity(
        entity_id="wolf_1",
        name="Wolf",
        x=14,
        y=9,
        sprite_key="s_monster",
        hostile=True,
        hp=10,
        max_hp=10,
        ap=50,
        attack=3,
        defense=1,
    )

    place = Place(
        place_id="tutorial_wilderness",
        name="Tutorial Wilderness",
        width=width,
        height=height,
        terrain_defs=terrain_defs,
        tiles=tiles,
        npcs=[npc],
        monsters=[wolf],
        chests=[chest],
    )
    return place, party
