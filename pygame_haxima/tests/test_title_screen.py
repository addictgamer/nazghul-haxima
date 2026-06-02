from __future__ import annotations

from pathlib import Path

import pygame

from pygame_haxima.data.asset_loader import AssetLoader
from pygame_haxima.engine.main_menu import MAIN_MENU_PANEL, main_menu_row_rect
from pygame_haxima.engine.title_screen import (
    load_title_splash,
    splash_filename_for_display,
    title_art_rect,
)


def test_splash_filename_matches_kern_init_for_1280x960() -> None:
    assert splash_filename_for_display(1280, 960) == "splash.png"
    assert splash_filename_for_display(640, 480) == "640x480_splash.png"


def test_load_title_splash_from_world_assets() -> None:
    pygame.init()
    root = Path(__file__).resolve().parents[1]
    loader = AssetLoader(project_root=root)
    splash = load_title_splash(loader)
    assert splash is not None
    assert splash.get_width() > 200
    assert splash.get_height() > 200
    pygame.quit()


def test_main_menu_panel_sits_in_sidebar() -> None:
    art = title_art_rect(1280, 960)
    assert art.right <= 960
    assert MAIN_MENU_PANEL.left >= 960
    row0 = main_menu_row_rect(0)
    assert row0.x >= MAIN_MENU_PANEL.x
