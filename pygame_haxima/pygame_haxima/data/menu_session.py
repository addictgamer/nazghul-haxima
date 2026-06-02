from __future__ import annotations

from pygame_haxima.domain.models import Entity, GameSession, Party, Place, Terrain, Tile


def build_menu_session() -> GameSession:
    """Minimal session used before a game is started or after returning to title."""
    terrain = Terrain(
        "menu_floor",
        "Floor",
        passable=True,
        glyph=".",
        color=(40, 44, 58),
        sprite_key=None,
    )
    place = Place(
        place_id="main_menu",
        name="Main Menu",
        width=1,
        height=1,
        terrain_defs={"menu_floor": terrain},
        tiles=[[Tile(terrain_id="menu_floor")]],
    )
    lead = Entity(
        entity_id="menu_avatar",
        name="Wanderer",
        x=0,
        y=0,
        sprite_key="s_wanderer",
        hp=1,
        max_hp=1,
    )
    party = Party(x=0, y=0, members=[lead])
    session = GameSession(place=place, party=party)
    session.show_main_menu = True
    session.main_menu_selected_index = 0
    session.command_prompt = "Main Menu> Up/Down select, Enter confirm, mouse click"
    session.log_lines = ["Welcome to Pygame Haxima."]
    return session
