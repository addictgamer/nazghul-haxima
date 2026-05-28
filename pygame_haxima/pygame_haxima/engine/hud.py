from __future__ import annotations

import pygame

from pygame_haxima.domain.models import GameSession, Mode
from pygame_haxima.engine.spells import get_spell


class HudPane:
    def __init__(self) -> None:
        self.font = pygame.font.SysFont("consolas", 20)
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
        status_parts: list[str] = []
        adjacent = self._adjacent_hostile_names(session)
        if adjacent:
            status_parts.append(f"Encounter: {', '.join(adjacent[:2])}")
        if session.party.ward_charges > 0:
            status_parts.append(f"Effects: Ward({session.party.ward_charges})")
        if status_parts:
            status_text = " | ".join(status_parts)
            y = self._blit_wrapped_line(
                surface,
                self.sub_font,
                status_text,
                (225, 200, 165),
                rect.x + 10,
                y,
                max_width,
                rect.bottom - 4,
            )
        self._draw_spell_status(surface, rect, session, max(y, rect.y + 50))
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

    def _draw_spell_status(
        self, surface: pygame.Surface, rect: pygame.Rect, session: GameSession, y: int
    ) -> None:
        spell = get_spell(session.party.selected_spell)
        if spell is None:
            return
        casts = self._casts_available(session)
        cast_text = f"Spell {spell.name} | Casts: {casts}"
        cast_render = self.sub_font.render(cast_text, True, (190, 215, 245))
        if y + cast_render.get_height() > rect.bottom - 3:
            return
        surface.blit(cast_render, (rect.x + 10, y))

        rx = rect.x + 280
        for reagent, required in sorted(spell.reagents.items()):
            available = int(session.party.reagents.get(reagent, 0))
            label = f"{reagent}({available})"
            if available <= 0:
                color = (255, 110, 110)
            elif available < required:
                color = (255, 190, 120)
            else:
                color = (170, 210, 180)
            reagent_render = self.sub_font.render(label, True, color)
            if rx + reagent_render.get_width() > rect.right - 8:
                break
            surface.blit(reagent_render, (rx, y))
            rx += reagent_render.get_width() + 14

    def _casts_available(self, session: GameSession) -> int:
        spell = get_spell(session.party.selected_spell)
        if spell is None:
            return 0
        caps: list[int] = []
        for reagent, qty in spell.reagents.items():
            if qty <= 0:
                continue
            available = int(session.party.reagents.get(reagent, 0))
            caps.append(available // qty)
        if not caps:
            return 0
        return min(caps)
