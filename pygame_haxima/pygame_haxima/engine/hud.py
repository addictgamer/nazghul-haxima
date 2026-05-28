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
        y = rect.y + 30
        adjacent = self._adjacent_hostile_names(session)
        if adjacent:
            encounter = f"Encounter nearby: {', '.join(adjacent[:2])}"
            surface.blit(self.font.render(encounter, True, (255, 145, 120)), (rect.x + 10, y))
            y += 22
        if session.debug_sprite_warnings:
            warn = (
                f"Terrain fallback keys: {session.terrain_fallback_key_count} "
                f"({', '.join(session.terrain_fallback_keys[:3])})"
            )
            surface.blit(self.font.render(warn, True, (255, 180, 120)), (rect.x + 10, y))

    def _adjacent_hostile_names(self, session: GameSession) -> list[str]:
        names: list[str] = []
        for monster in session.place.monsters:
            if not monster.is_alive():
                continue
            if abs(monster.x - session.party.x) + abs(monster.y - session.party.y) <= 1:
                names.append(monster.name)
        return names
