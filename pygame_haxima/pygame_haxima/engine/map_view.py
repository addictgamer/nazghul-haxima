from __future__ import annotations

import pygame

from pygame_haxima.config import DISPLAY
from pygame_haxima.data.sprite_atlas import SpriteAtlas
from pygame_haxima.domain.models import GameSession
from pygame_haxima.engine.item_sprites import item_sprite_key


class MapView:
    def __init__(self, atlas: SpriteAtlas) -> None:
        self.atlas = atlas
        self.tile_w = DISPLAY.tile_w
        self.tile_h = DISPLAY.tile_h
        self.debug_font = pygame.font.SysFont("consolas", 12)
        self.feedback_font = pygame.font.SysFont("consolas", 18, bold=True)

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
        self._draw_target_candidates(surface, viewport, start_x, start_y, session)
        if session.target_cursor is not None:
            self._draw_target_cursor(surface, viewport, start_x, start_y, session)
        self._draw_combat_feedback(surface, viewport, start_x, start_y, session)

    def compute_view_window(
        self, viewport: pygame.Rect, session: GameSession
    ) -> tuple[int, int, int, int]:
        place = session.place
        visible_w = max(1, viewport.width // self.tile_w)
        visible_h = max(1, viewport.height // self.tile_h)
        max_start_x = max(0, place.width - visible_w)
        max_start_y = max(0, place.height - visible_h)

        # Initialize camera centered on party.
        if session.camera_start_x is None or session.camera_start_y is None:
            half_w = visible_w // 2
            half_h = visible_h // 2
            start_x = max(0, min(session.party.x - half_w, max_start_x))
            start_y = max(0, min(session.party.y - half_h, max_start_y))
        else:
            start_x = max(0, min(session.camera_start_x, max_start_x))
            start_y = max(0, min(session.camera_start_y, max_start_y))

        # Deadzone follow: only move camera when party leaves margin.
        deadzone_x = max(1, min(session.camera_deadzone_tiles, max(1, visible_w // 2)))
        deadzone_y = max(1, min(session.camera_deadzone_tiles, max(1, visible_h // 2)))

        party_view_x = session.party.x - start_x
        party_view_y = session.party.y - start_y

        left_bound = deadzone_x
        right_bound = max(left_bound, visible_w - deadzone_x - 1)
        top_bound = deadzone_y
        bottom_bound = max(top_bound, visible_h - deadzone_y - 1)

        if party_view_x < left_bound:
            start_x -= left_bound - party_view_x
        elif party_view_x > right_bound:
            start_x += party_view_x - right_bound

        if party_view_y < top_bound:
            start_y -= top_bound - party_view_y
        elif party_view_y > bottom_bound:
            start_y += party_view_y - bottom_bound

        start_x = max(0, min(start_x, max_start_x))
        start_y = max(0, min(start_y, max_start_y))
        session.camera_start_x = start_x
        session.camera_start_y = start_y

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
        party_sprite = session.party.lead().sprite_key if session.party.members else "s_wanderer"
        drawables: list[tuple[str, int, int]] = [(party_sprite, session.party.x, session.party.y)]
        drawables.extend((npc.sprite_key, npc.x, npc.y) for npc in session.place.npcs)
        drawables.extend(
            (monster.sprite_key, monster.x, monster.y)
            for monster in session.place.monsters
            if monster.is_alive()
        )
        drawables.extend(
            (chest.sprite_key, chest.x, chest.y) for chest in session.place.chests if not chest.opened
        )
        drawables.extend(
            (item_sprite_key(items[0]), x, y)
            for (x, y), items in session.place.ground_items.items()
            if items
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
        pulse = 2 + (session.ui_anim_tick % 3)
        pygame.draw.rect(surface, color, rect, pulse)
        pygame.draw.rect(surface, (20, 20, 20), rect, 1)
        self._draw_target_trail(surface, viewport, start_x, start_y, session, rect)

    def _draw_terrain_debug(self, surface: pygame.Surface, cell: pygame.Rect, terrain_id: str) -> None:
        tag = self.debug_font.render(terrain_id[:5], True, (240, 245, 200))
        shadow = self.debug_font.render(terrain_id[:5], True, (20, 20, 20))
        surface.blit(shadow, (cell.x + 2, cell.y + 2))
        surface.blit(tag, (cell.x + 1, cell.y + 1))

    def _draw_target_trail(
        self,
        surface: pygame.Surface,
        viewport: pygame.Rect,
        start_x: int,
        start_y: int,
        session: GameSession,
        target_rect: pygame.Rect,
    ) -> None:
        if session.target_cursor is None:
            return
        px = viewport.x + (session.party.x - start_x) * self.tile_w + self.tile_w // 2
        py = viewport.y + (session.party.y - start_y) * self.tile_h + self.tile_h // 2
        tx = target_rect.x + self.tile_w // 2
        ty = target_rect.y + self.tile_h // 2
        trail_color = (180, 210, 255) if session.targeting_action == "examine" else (255, 240, 170)
        pygame.draw.line(surface, trail_color, (px, py), (tx, ty), 1)

    def _draw_target_candidates(
        self,
        surface: pygame.Surface,
        viewport: pygame.Rect,
        start_x: int,
        start_y: int,
        session: GameSession,
    ) -> None:
        action = session.targeting_action
        if action not in {"talk", "open", "attack"}:
            return
        candidates = [
            (session.party.x, session.party.y),
            (session.party.x + 1, session.party.y),
            (session.party.x - 1, session.party.y),
            (session.party.x, session.party.y + 1),
            (session.party.x, session.party.y - 1),
        ]
        alpha = 55 + (session.ui_anim_tick % 5) * 10
        for x, y in candidates:
            if x < start_x or y < start_y:
                continue
            if not session.place.in_bounds(x, y):
                continue
            color = self._target_color(session, x, y)
            if color[0] > 200 and color[1] < 180:
                continue
            px = viewport.x + (x - start_x) * self.tile_w
            py = viewport.y + (y - start_y) * self.tile_h
            overlay = pygame.Surface((self.tile_w, self.tile_h), pygame.SRCALPHA)
            overlay.fill((color[0], color[1], color[2], alpha))
            surface.blit(overlay, (px, py))

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
        self,
        surface: pygame.Surface,
        viewport: pygame.Rect,
        start_x: int,
        start_y: int,
        session: GameSession,
    ) -> None:
        if session.combat_feedback_ticks <= 0 or not session.combat_feedback_text:
            return
        alpha = min(210, max(140, session.combat_feedback_ticks * 5))
        banner = pygame.Surface((420, 54), pygame.SRCALPHA)
        banner.fill((10, 10, 14, alpha))
        pygame.draw.rect(banner, (240, 240, 240, min(255, alpha)), banner.get_rect(), 2)
        text_shadow = self.feedback_font.render(session.combat_feedback_text, True, (0, 0, 0))
        text = self.feedback_font.render(session.combat_feedback_text, True, session.combat_feedback_color)
        text_x = 16
        text_y = (banner.get_height() - text.get_height()) // 2
        banner.blit(text_shadow, (text_x + 2, text_y + 2))
        banner.blit(text, (text_x, text_y))

        pos_x = viewport.centerx - banner.get_width() // 2
        pos_y = viewport.y + 10
        anchor = session.combat_feedback_world_pos
        if anchor is not None:
            ax, ay = anchor
            if start_x <= ax < start_x + (viewport.width // self.tile_w) and start_y <= ay < start_y + (
                viewport.height // self.tile_h
            ):
                tile_center_x = viewport.x + (ax - start_x) * self.tile_w + self.tile_w // 2
                tile_top_y = viewport.y + (ay - start_y) * self.tile_h
                pos_x = tile_center_x - banner.get_width() // 2
                pos_y = tile_top_y - banner.get_height() - 8

        pos_x = max(viewport.x + 4, min(pos_x, viewport.right - banner.get_width() - 4))
        pos_y = max(viewport.y + 4, min(pos_y, viewport.bottom - banner.get_height() - 4))
        surface.blit(banner, (pos_x, pos_y))
