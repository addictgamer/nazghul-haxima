from __future__ import annotations

import pygame

from pygame_haxima.config import DISPLAY

MAIN_MENU_ITEMS: tuple[tuple[str, str], ...] = (
    ("new_game", "New Game"),
    ("load_game", "Load Game"),
    ("options", "Options"),
    ("quit", "Quit"),
)

MAIN_MENU_PANEL = pygame.Rect(390, 260, 500, 340)
MAIN_MENU_ROW_HEIGHT = 52
MAIN_MENU_TITLE_Y = 120


def main_menu_row_rect(index: int) -> pygame.Rect:
    return pygame.Rect(
        MAIN_MENU_PANEL.x + 24,
        MAIN_MENU_PANEL.y + 72 + index * MAIN_MENU_ROW_HEIGHT,
        MAIN_MENU_PANEL.width - 48,
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
) -> None:
    width, height = DISPLAY.base_width, DISPLAY.base_height
    surface.fill((8, 10, 18))
    vignette = pygame.Surface((width, height), pygame.SRCALPHA)
    for band in range(8):
        alpha = 12 + band * 4
        pygame.draw.rect(
            vignette,
            (30, 38, 70, alpha),
            pygame.Rect(0, band * (height // 8), width, height // 8),
        )
    surface.blit(vignette, (0, 0))

    title = title_font.render("Pygame Haxima", True, (245, 228, 160))
    subtitle = menu_font.render("A Nazghul-inspired redesign prototype", True, (170, 185, 215))
    tx = (width - title.get_width()) // 2
    surface.blit(title, (tx, MAIN_MENU_TITLE_Y))
    surface.blit(subtitle, ((width - subtitle.get_width()) // 2, MAIN_MENU_TITLE_Y + 40))

    pygame.draw.rect(surface, (22, 26, 42), MAIN_MENU_PANEL)
    pygame.draw.rect(surface, (150, 165, 210), MAIN_MENU_PANEL, 2)
    panel_title = menu_font.render("Main Menu", True, (230, 220, 170))
    surface.blit(panel_title, (MAIN_MENU_PANEL.x + 20, MAIN_MENU_PANEL.y + 16))

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
        "Arrows / W-S or mouse hover: navigate   Enter / click: select   Esc: back",
        True,
        (140, 155, 180),
    )
    surface.blit(hint, ((width - hint.get_width()) // 2, height - 36))
