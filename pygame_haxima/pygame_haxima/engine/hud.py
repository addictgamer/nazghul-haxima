from __future__ import annotations

import pygame

from pygame_haxima.domain.models import GameSession, Mode


class HudPane:
    def __init__(self) -> None:
        self.font = pygame.font.SysFont("consolas", 22)

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, session: GameSession) -> None:
        pygame.draw.rect(surface, (20, 20, 30), rect)
        pygame.draw.rect(surface, (90, 90, 120), rect, 1)
        mode = "COMBAT" if session.mode == Mode.COMBAT else "PARTY"
        text = (
            f"Turn {session.party.turn_count:04d}  "
            f"Time {session.clock_hours:02d}:{session.clock_minutes:02d}  "
            f"Food {session.party.food}  Gold {session.party.gold}  Mode {mode}"
        )
        surface.blit(self.font.render(text, True, (220, 220, 230)), (rect.x + 10, rect.y + 8))
