from __future__ import annotations

import pygame

from pygame_haxima.domain.models import GameSession, Mode


class HudPane:
    def __init__(self) -> None:
        self.font = pygame.font.SysFont("consolas", 22)
        self.sub_font = pygame.font.SysFont("consolas", 16)

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, session: GameSession) -> None:
        pygame.draw.rect(surface, (20, 20, 30), rect)
        pygame.draw.rect(surface, (90, 90, 120), rect, 1)
        mode = "COMBAT" if session.mode == Mode.COMBAT else "PARTY"
        text = (
            f"Turn {session.party.turn_count:04d}  "
            f"Time {session.clock_hours:02d}:{session.clock_minutes:02d}  "
            f"Food {session.party.food}  Gold {session.party.gold}  Mode {mode}"
        )
        max_width = rect.width - 20
        y = rect.y + 7
        y = self._blit_wrapped_line(
            surface,
            self.font,
            text,
            (220, 220, 230),
            rect.x + 10,
            y,
            max_width,
            rect.bottom - 4,
        )
        adjacent = self._adjacent_hostile_names(session)
        if adjacent:
            encounter = f"Encounter nearby: {', '.join(adjacent[:2])}"
            y = self._blit_wrapped_line(
                surface,
                self.sub_font,
                encounter,
                (255, 145, 120),
                rect.x + 10,
                y,
                max_width,
                rect.bottom - 4,
            )
        if session.party.ward_charges > 0:
            effect = f"Active effects: Ward({session.party.ward_charges})"
            y = self._blit_wrapped_line(
                surface,
                self.sub_font,
                effect,
                (170, 220, 255),
                rect.x + 10,
                y,
                max_width,
                rect.bottom - 4,
            )
        if session.debug_sprite_warnings:
            warn = (
                f"Terrain fallback keys: {session.terrain_fallback_key_count} "
                f"({', '.join(session.terrain_fallback_keys[:3])})"
            )
            self._blit_wrapped_line(
                surface,
                self.sub_font,
                warn,
                (255, 180, 120),
                rect.x + 10,
                y,
                max_width,
                rect.bottom - 4,
            )

    def _adjacent_hostile_names(self, session: GameSession) -> list[str]:
        names: list[str] = []
        for monster in session.place.monsters:
            if not monster.is_alive():
                continue
            if abs(monster.x - session.party.x) + abs(monster.y - session.party.y) <= 1:
                names.append(monster.name)
        return names

    def _wrap_text(self, font: pygame.font.Font, text: str, max_width: int) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _blit_wrapped_line(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        text: str,
        color: tuple[int, int, int],
        x: int,
        y: int,
        max_width: int,
        max_bottom: int,
    ) -> int:
        lines = self._wrap_text(font, text, max_width)
        for line in lines:
            rendered = font.render(line, True, color)
            if y + rendered.get_height() > max_bottom:
                return y
            surface.blit(rendered, (x, y))
            y += rendered.get_height() + 1
        return y
