from __future__ import annotations

import pygame

from pygame_haxima.config import DISPLAY
from pygame_haxima.data.sprite_atlas import SpriteAtlas
from pygame_haxima.domain.models import GameSession


class MapView:
    def __init__(self, atlas: SpriteAtlas) -> None:
        self.atlas = atlas
        self.tile_w = DISPLAY.tile_w
        self.tile_h = DISPLAY.tile_h
        self.debug_font = pygame.font.SysFont("consolas", 12)

    def draw(self, surface: pygame.Surface, viewport: pygame.Rect, session: GameSession) -> None:
        place = session.place
        start_x, start_y, end_x, end_y = self.compute_view_window(viewport, session)

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                terrain = place.terrain_at(x, y)
                cell = pygame.Rect(
                    viewport.x + (x - start_x) * self.tile_w,
                    viewport.y + (y - start_y) * self.tile_h,
                    self.tile_w,
                    self.tile_h,
                )
                if terrain.sprite_key:
                    surface.blit(self.atlas.get(terrain.sprite_key), cell.topleft)
                else:
                    pygame.draw.rect(surface, terrain.color, cell)
                pygame.draw.rect(surface, (20, 20, 20), cell, 1)
                if session.debug_terrain_ids:
                    self._draw_terrain_debug(surface, cell, terrain.terrain_id)

        self._draw_entities(surface, viewport, start_x, start_y, session)
        self._draw_encounter_indicators(surface, viewport, start_x, start_y, session)
        if session.target_cursor is not None:
            self._draw_target_cursor(surface, viewport, start_x, start_y, session)
        self._draw_combat_feedback(surface, viewport, session)

    def compute_view_window(
        self, viewport: pygame.Rect, session: GameSession
    ) -> tuple[int, int, int, int]:
        place = session.place
        visible_w = max(1, viewport.width // self.tile_w)
        visible_h = max(1, viewport.height // self.tile_h)
        half_w = visible_w // 2
        half_h = visible_h // 2
        cam_x, cam_y = session.party.x, session.party.y

        max_start_x = max(0, place.width - visible_w)
        max_start_y = max(0, place.height - visible_h)
        start_x = max(0, min(cam_x - half_w, max_start_x))
        start_y = max(0, min(cam_y - half_h, max_start_y))
        end_x = min(place.width, start_x + visible_w)
        end_y = min(place.height, start_y + visible_h)
        return start_x, start_y, end_x, end_y

    def _draw_entities(
        self,
        surface: pygame.Surface,
        viewport: pygame.Rect,
        start_x: int,
        start_y: int,
        session: GameSession,
    ) -> None:
        drawables: list[tuple[str, int, int]] = [("s_party", session.party.x, session.party.y)]
        drawables.extend((npc.sprite_key, npc.x, npc.y) for npc in session.place.npcs)
        drawables.extend(
            (monster.sprite_key, monster.x, monster.y)
            for monster in session.place.monsters
            if monster.is_alive()
        )
        drawables.extend(
            ("s_chest", chest.x, chest.y) for chest in session.place.chests if not chest.opened
        )
        for sprite_key, x, y in drawables:
            if x < start_x or y < start_y:
                continue
            px = viewport.x + (x - start_x) * self.tile_w
            py = viewport.y + (y - start_y) * self.tile_h
            surface.blit(self.atlas.get(sprite_key), (px, py))

    def _draw_target_cursor(
        self,
        surface: pygame.Surface,
        viewport: pygame.Rect,
        start_x: int,
        start_y: int,
        session: GameSession,
    ) -> None:
        target = session.target_cursor
        if target is None:
            return
        x, y = target
        px = viewport.x + (x - start_x) * self.tile_w
        py = viewport.y + (y - start_y) * self.tile_h
        rect = pygame.Rect(px, py, self.tile_w, self.tile_h)
        color = self._target_color(session, x, y)
        pygame.draw.rect(surface, color, rect, 2)
        pygame.draw.rect(surface, (20, 20, 20), rect, 1)

    def _draw_terrain_debug(self, surface: pygame.Surface, cell: pygame.Rect, terrain_id: str) -> None:
        tag = self.debug_font.render(terrain_id[:5], True, (240, 245, 200))
        shadow = self.debug_font.render(terrain_id[:5], True, (20, 20, 20))
        surface.blit(shadow, (cell.x + 2, cell.y + 2))
        surface.blit(tag, (cell.x + 1, cell.y + 1))

    def _target_color(self, session: GameSession, x: int, y: int) -> tuple[int, int, int]:
        action = session.targeting_action
        if action is None:
            return (255, 245, 120)
        if action == "examine":
            return (120, 220, 255)
        in_range = abs(session.party.x - x) + abs(session.party.y - y) <= 1
        if not in_range:
            return (255, 120, 120)
        if action == "talk":
            return (140, 255, 160) if session.place.npc_at(x, y) is not None else (255, 120, 120)
        if action == "open":
            chest = session.place.chest_at(x, y)
            return (140, 255, 160) if chest is not None and not chest.opened else (255, 120, 120)
        if action == "attack":
            return (140, 255, 160) if session.place.monster_at(x, y) is not None else (255, 120, 120)
        return (255, 245, 120)

    def _draw_encounter_indicators(
        self,
        surface: pygame.Surface,
        viewport: pygame.Rect,
        start_x: int,
        start_y: int,
        session: GameSession,
    ) -> None:
        for monster in session.place.monsters:
            if not monster.is_alive():
                continue
            if abs(monster.x - session.party.x) + abs(monster.y - session.party.y) > 1:
                continue
            px = viewport.x + (monster.x - start_x) * self.tile_w
            py = viewport.y + (monster.y - start_y) * self.tile_h
            rect = pygame.Rect(px, py, self.tile_w, self.tile_h)
            pygame.draw.rect(surface, (255, 80, 80), rect, 2)

    def _draw_combat_feedback(
        self, surface: pygame.Surface, viewport: pygame.Rect, session: GameSession
    ) -> None:
        if session.combat_feedback_ticks <= 0 or not session.combat_feedback_text:
            return
        alpha = min(255, max(0, session.combat_feedback_ticks * 7))
        banner = pygame.Surface((300, 32), pygame.SRCALPHA)
        banner.fill((20, 20, 28, alpha // 2))
        text = self.debug_font.render(session.combat_feedback_text, True, session.combat_feedback_color)
        banner.blit(text, (8, 8))
        surface.blit(banner, (viewport.centerx - 150, viewport.y + 12))
