from __future__ import annotations

import pygame

from pygame_haxima.config import DISPLAY
from pygame_haxima.engine.title_screen import (
    TITLE_HUD_HEIGHT,
    TITLE_SIDEBAR_WIDTH,
    blit_splash_in_rect,
    draw_title_backdrop,
    title_art_rect,
)

MAIN_MENU_ITEMS: tuple[tuple[str, str], ...] = (
    ("new_game", "New Game"),
    ("load_game", "Load Game"),
    ("options", "Options"),
    ("quit", "Quit"),
)

# Menu list in the right sidebar, matching in-game layout proportions.
MAIN_MENU_PANEL = pygame.Rect(
    DISPLAY.base_width - TITLE_SIDEBAR_WIDTH + 16,
    TITLE_HUD_HEIGHT + 24,
    TITLE_SIDEBAR_WIDTH - 32,
    380,
)
MAIN_MENU_ROW_HEIGHT = 52


def main_menu_row_rect(index: int) -> pygame.Rect:
    return pygame.Rect(
        MAIN_MENU_PANEL.x + 8,
        MAIN_MENU_PANEL.y + 56 + index * MAIN_MENU_ROW_HEIGHT,
        MAIN_MENU_PANEL.width - 16,
        MAIN_MENU_ROW_HEIGHT - 8,
    )


def main_menu_index_at(ui_pos: tuple[int, int]) -> int | None:
    x, y = ui_pos
    for index, _entry in enumerate(MAIN_MENU_ITEMS):
        if main_menu_row_rect(index).collidepoint((x, y)):
            return index
    return None


def main_menu_hit_test(ui_pos: tuple[int, int]) -> str | None:
    index = main_menu_index_at(ui_pos)
    if index is None:
        return None
    return MAIN_MENU_ITEMS[index][0]


def draw_main_menu(
    surface: pygame.Surface,
    *,
    selected_index: int,
    title_font: pygame.font.Font,
    menu_font: pygame.font.Font,
    small_font: pygame.font.Font,
    splash: pygame.Surface | None = None,
) -> None:
    width, height = DISPLAY.base_width, DISPLAY.base_height
    surface.fill((8, 10, 18))

    # Top bar (title strip, like the in-game HUD band).
    hud = pygame.Rect(0, 0, width, TITLE_HUD_HEIGHT)
    pygame.draw.rect(surface, (18, 22, 34), hud)
    pygame.draw.rect(surface, (110, 120, 150), hud, 1)
    if splash is not None:
        header = title_font.render("Haxima", True, (245, 228, 160))
    else:
        header = title_font.render("Pygame Haxima", True, (245, 228, 160))
    surface.blit(header, (20, 18))

    art_area = title_art_rect(width, height)
    draw_title_backdrop(surface, art_area)
    if splash is not None:
        blit_splash_in_rect(surface, splash, art_area)
    else:
        fallback = menu_font.render(
            "(splash.png not found in worlds/haxima-1.002)",
            True,
            (140, 150, 170),
        )
        surface.blit(
            fallback,
            (
                art_area.x + (art_area.width - fallback.get_width()) // 2,
                art_area.centery - fallback.get_height() // 2,
            ),
        )

    sidebar = pygame.Rect(width - TITLE_SIDEBAR_WIDTH, TITLE_HUD_HEIGHT, TITLE_SIDEBAR_WIDTH, height - TITLE_HUD_HEIGHT)
    pygame.draw.rect(surface, (14, 16, 26), sidebar)
    pygame.draw.rect(surface, (90, 100, 130), sidebar, 1)

    pygame.draw.rect(surface, (22, 26, 42), MAIN_MENU_PANEL)
    pygame.draw.rect(surface, (150, 165, 210), MAIN_MENU_PANEL, 2)
    panel_title = menu_font.render("Main Menu", True, (230, 220, 170))
    surface.blit(panel_title, (MAIN_MENU_PANEL.x + 12, MAIN_MENU_PANEL.y + 12))

    for index, (_action_id, label) in enumerate(MAIN_MENU_ITEMS):
        row = main_menu_row_rect(index)
        selected = index == selected_index
        fill = (72, 92, 140) if selected else (32, 38, 58)
        border = (240, 245, 255) if selected else (100, 115, 150)
        pygame.draw.rect(surface, fill, row)
        pygame.draw.rect(surface, border, row, 2 if selected else 1)
        prefix = ">" if selected else " "
        color = (250, 250, 255) if selected else (185, 195, 220)
        text = menu_font.render(f"{prefix} {label}", True, color)
        surface.blit(text, (row.x + 14, row.y + (row.height - text.get_height()) // 2))

    hint = small_font.render(
        "Arrows / W-S or hover: navigate   Enter / click: select",
        True,
        (140, 155, 180),
    )
    surface.blit(hint, ((width - hint.get_width()) // 2, height - 32))
