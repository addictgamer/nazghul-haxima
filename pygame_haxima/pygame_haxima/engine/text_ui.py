from __future__ import annotations

import pygame

from pygame_haxima.domain.models import GameSession


class TextUi:
    def __init__(self) -> None:
        self.console_font = pygame.font.SysFont("consolas", 20)
        self.cmd_font = pygame.font.SysFont("consolas", 22, bold=True)

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
