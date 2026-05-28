from __future__ import annotations

import pygame

from pygame_haxima.config import DISPLAY
from pygame_haxima.domain.models import GameSession
from pygame_haxima.engine.hud import HudPane
from pygame_haxima.engine.map_view import MapView
from pygame_haxima.engine.text_ui import TextUi


class Renderer:
    def __init__(self, map_view: MapView, hud: HudPane, text_ui: TextUi) -> None:
        self.map_view = map_view
        self.hud = hud
        self.text_ui = text_ui
        self.base_size = (DISPLAY.base_width, DISPLAY.base_height)
        self.scale = self._startup_scale()
        self.virtual_surface = pygame.Surface(self.base_size)
        self.window = self._create_window(fullscreen=DISPLAY.fullscreen)
        self.is_fullscreen = DISPLAY.fullscreen
        self.rects = self._layout_rects()

    def _startup_scale(self) -> int:
        preferred = 2
        fallback = max(1, DISPLAY.scale)
        desktop_w = 0
        desktop_h = 0

        sizes = pygame.display.get_desktop_sizes()
        if sizes:
            desktop_w, desktop_h = sizes[0]
        else:
            info = pygame.display.Info()
            desktop_w = info.current_w
            desktop_h = info.current_h

        if desktop_w <= 0 or desktop_h <= 0:
            return fallback
        if DISPLAY.base_width * preferred <= desktop_w and DISPLAY.base_height * preferred <= desktop_h:
            return preferred
        return fallback

    def _create_window(self, fullscreen: bool) -> pygame.Surface:
        flags = pygame.FULLSCREEN if fullscreen else 0
        width = DISPLAY.base_width * self.scale
        height = DISPLAY.base_height * self.scale
        return pygame.display.set_mode((width, height), flags)

    def toggle_fullscreen(self) -> None:
        self.is_fullscreen = not self.is_fullscreen
        self.window = self._create_window(self.is_fullscreen)

    def set_scale(self, scale: int) -> None:
        self.scale = max(1, scale)
        self.window = self._create_window(self.is_fullscreen)

    def _layout_rects(self) -> dict[str, pygame.Rect]:
        hud_h = 70
        cmd_h = 38
        console_h = 200
        sidebar_w = 320
        main_w = DISPLAY.base_width - sidebar_w
        map_h = DISPLAY.base_height - (hud_h + console_h + cmd_h)
        return {
            "hud": pygame.Rect(0, 0, DISPLAY.base_width, hud_h),
            "map": pygame.Rect(0, hud_h, main_w, map_h),
            "console": pygame.Rect(0, hud_h + map_h, main_w, console_h),
            "cmd": pygame.Rect(0, DISPLAY.base_height - cmd_h, main_w, cmd_h),
            "sidebar": pygame.Rect(main_w, hud_h, sidebar_w, DISPLAY.base_height - hud_h),
        }

    def render(self, session: GameSession) -> None:
        target = self.virtual_surface
        target.fill((0, 0, 0))
        self.map_view.draw(target, self.rects["map"], session)
        self.hud.draw(target, self.rects["hud"], session)
        self.text_ui.draw_console(target, self.rects["console"], session)
        self.text_ui.draw_command(target, self.rects["cmd"], session)
        self.text_ui.draw_sidebar(target, self.rects["sidebar"], session)

        if self.scale == 1:
            self.window.blit(target, (0, 0))
        else:
            scaled = pygame.transform.scale(
                target, (DISPLAY.base_width * self.scale, DISPLAY.base_height * self.scale)
            )
            self.window.blit(scaled, (0, 0))
        pygame.display.flip()

    def screen_to_map_tile(self, pos: tuple[int, int], session: GameSession) -> tuple[int, int] | None:
        x, y = pos
        if self.scale != 1:
            x //= self.scale
            y //= self.scale
        map_rect = self.rects["map"]
        if not map_rect.collidepoint((x, y)):
            return None
        tile_x = (x - map_rect.x) // DISPLAY.tile_w
        tile_y = (y - map_rect.y) // DISPLAY.tile_h
        start_x, start_y, _, _ = self.map_view.compute_view_window(map_rect, session)
        world_x = start_x + tile_x
        world_y = start_y + tile_y
        if not session.place.in_bounds(world_x, world_y):
            return None
        return world_x, world_y
