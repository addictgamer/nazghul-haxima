from __future__ import annotations

from pathlib import Path

from pygame_haxima.data.content_registry import ContentRegistry
from pygame_haxima.data.menu_session import build_menu_session
from pygame_haxima.engine.loop import TurnLoop
from pygame_haxima.engine.main_menu import main_menu_hit_test, main_menu_row_rect


def test_menu_session_starts_on_main_menu() -> None:
    session = build_menu_session()
    assert session.show_main_menu is True
    assert session.place.place_id == "main_menu"


def test_main_menu_hit_test_maps_rows() -> None:
    row0 = main_menu_row_rect(0)
    row1 = main_menu_row_rect(1)
    assert main_menu_hit_test((row0.centerx, row0.centery)) == "new_game"
    assert main_menu_hit_test((row1.centerx, row1.centery)) == "load_game"


def test_make_new_session_leaves_main_menu() -> None:
    root = Path(__file__).resolve().parents[1]
    registry = ContentRegistry(root)
    menu = registry.make_menu_session()
    game = registry.make_new_session()
    assert menu.show_main_menu is True
    assert game.show_main_menu is False
    assert game.place.place_id != "main_menu"


class _FakeRenderer:
    scale = 2
    is_fullscreen = False

    def set_scale(self, scale: int) -> None:
        self.scale = scale

    def toggle_fullscreen(self) -> None:
        self.is_fullscreen = not self.is_fullscreen


def test_new_game_from_menu_replaces_session() -> None:
    root = Path(__file__).resolve().parents[1]
    registry = ContentRegistry(root)
    menu = registry.make_menu_session()
    loop = TurnLoop(
        renderer=_FakeRenderer(),  # type: ignore[arg-type]
        audio=object(),  # type: ignore[arg-type]
        save_manager=object(),  # type: ignore[arg-type]
        content_registry=registry,
    )
    loop._start_new_game_from_menu(menu)
    assert loop.session_replacement is not None
    assert loop.session_replacement.show_main_menu is False
    assert loop.session_replacement.place.place_id != "main_menu"
