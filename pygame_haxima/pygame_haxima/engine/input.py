from __future__ import annotations

import pygame

from pygame_haxima.engine.events import ANIMATION_EVENT, EngineEvent, EngineEventType
from pygame_haxima.engine.keymap import KeyMap
from pygame_haxima.engine.renderer import Renderer
from pygame_haxima.domain.models import GameSession


class InputController:
    def __init__(self, keymap: KeyMap, renderer: Renderer) -> None:
        self.keymap = keymap
        self.renderer = renderer
        self._spellbook_down_initial_ms: int | None = None
        self._spellbook_down_last_repeat_ms: int | None = None
        self._spellbook_repeat_delay_ms = 350
        self._spellbook_repeat_interval_ms = 75

    def poll(self, session: GameSession) -> list[EngineEvent]:
        events: list[EngineEvent] = []
        for pg_event in pygame.event.get():
            if pg_event.type == pygame.QUIT:
                events.append(EngineEvent(EngineEventType.QUIT, {}))
            elif pg_event.type == ANIMATION_EVENT:
                events.append(EngineEvent(EngineEventType.ANIMATION_TICK, {}))
            elif pg_event.type == pygame.KEYDOWN:
                action = self.keymap.action_for_key(pg_event.key)
                if action is not None:
                    events.append(EngineEvent(EngineEventType.ACTION, {"action": action}))
            elif pg_event.type == pygame.KEYUP:
                if pg_event.key == pygame.K_DOWN:
                    self._reset_spellbook_down_repeat()
            elif pg_event.type == pygame.MOUSEBUTTONDOWN and pg_event.button == 1:
                ui_pos = self.renderer.window_to_virtual(pg_event.pos)
                events.append(EngineEvent(EngineEventType.MOUSE_CLICK, {"ui_pos": ui_pos}))
                tile = self.renderer.screen_to_map_tile(pg_event.pos, session)
                if tile is not None:
                    events.append(EngineEvent(EngineEventType.MOUSE_TILE, {"tile": tile}))
            elif pg_event.type == pygame.MOUSEMOTION:
                ui_pos = self.renderer.window_to_virtual(pg_event.pos)
                events.append(EngineEvent(EngineEventType.MOUSE_MOVE, {"ui_pos": ui_pos}))
            elif pg_event.type == pygame.MOUSEWHEEL:
                events.append(EngineEvent(EngineEventType.MOUSE_WHEEL, {"y": int(pg_event.y)}))
        self._append_spellbook_down_repeat(session, events)
        return events

    def _append_spellbook_down_repeat(self, session: GameSession, events: list[EngineEvent]) -> None:
        if not session.show_spellbook_menu:
            self._reset_spellbook_down_repeat()
            return
        pressed = pygame.key.get_pressed()[pygame.K_DOWN]
        if not pressed:
            self._reset_spellbook_down_repeat()
            return

        now_ms = pygame.time.get_ticks()
        if self._spellbook_down_initial_ms is None:
            self._spellbook_down_initial_ms = now_ms
            self._spellbook_down_last_repeat_ms = None
            return

        if now_ms - self._spellbook_down_initial_ms < self._spellbook_repeat_delay_ms:
            return
        if self._spellbook_down_last_repeat_ms is None or (
            now_ms - self._spellbook_down_last_repeat_ms >= self._spellbook_repeat_interval_ms
        ):
            events.append(EngineEvent(EngineEventType.ACTION, {"action": "move_s"}))
            self._spellbook_down_last_repeat_ms = now_ms

    def _reset_spellbook_down_repeat(self) -> None:
        self._spellbook_down_initial_ms = None
        self._spellbook_down_last_repeat_ms = None
