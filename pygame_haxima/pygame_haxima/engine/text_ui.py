from __future__ import annotations

import pygame

from pygame_haxima.domain.models import GameSession


class TextUi:
    def __init__(self) -> None:
        self.console_font = pygame.font.SysFont("consolas", 20)
        self.cmd_font = pygame.font.SysFont("consolas", 22, bold=True)
        self.menu_font = pygame.font.SysFont("consolas", 20)

    def draw_console(self, surface: pygame.Surface, rect: pygame.Rect, session: GameSession) -> None:
        pygame.draw.rect(surface, (12, 12, 16), rect)
        pygame.draw.rect(surface, (80, 80, 95), rect, 1)
        lines = session.log_lines[-8:]
        for index, line in enumerate(lines):
            rendered = self.console_font.render(line[:110], True, (190, 210, 190))
            surface.blit(rendered, (rect.x + 8, rect.y + 8 + index * 20))

    def draw_command(self, surface: pygame.Surface, rect: pygame.Rect, session: GameSession) -> None:
        pygame.draw.rect(surface, (16, 16, 22), rect)
        pygame.draw.rect(surface, (110, 110, 140), rect, 1)
        prompt = self.cmd_font.render(session.command_prompt, True, (230, 220, 120))
        surface.blit(prompt, (rect.x + 8, rect.y + 6))
        if session.show_options_menu:
            self.draw_options_menu(surface, session)

    def draw_options_menu(self, surface: pygame.Surface, session: GameSession) -> None:
        panel = pygame.Rect(170, 170, 940, 520)
        pygame.draw.rect(surface, (20, 22, 34), panel)
        pygame.draw.rect(surface, (160, 170, 210), panel, 2)

        title = self.cmd_font.render("Options", True, (245, 235, 180))
        surface.blit(title, (panel.x + 16, panel.y + 12))

        options = [
            f"Scale: {session.option_scale}x",
            f"Fullscreen: {'On' if session.option_fullscreen else 'Off'}",
            f"Terrain IDs (F2): {'On' if session.debug_terrain_ids else 'Off'}",
            f"Sprite warnings (F3): {'On' if session.debug_sprite_warnings else 'Off'}",
        ]
        for index, text in enumerate(options):
            color = (240, 240, 255) if index == session.options_selected_index else (170, 180, 200)
            prefix = ">" if index == session.options_selected_index else " "
            line = self.menu_font.render(f"{prefix} {text}", True, color)
            surface.blit(line, (panel.x + 20, panel.y + 60 + index * 28))

        hint = self.menu_font.render("Use arrows: up/down select, left/right change, Esc/F10 close", True, (215, 205, 140))
        surface.blit(hint, (panel.x + 20, panel.y + 190))

        preview_title = self.menu_font.render("Keybind preview:", True, (200, 220, 240))
        surface.blit(preview_title, (panel.x + 20, panel.y + 235))
        for index, line in enumerate(session.keybind_preview[:9]):
            row = self.menu_font.render(f"- {line}", True, (175, 195, 220))
            surface.blit(row, (panel.x + 28, panel.y + 265 + index * 24))
