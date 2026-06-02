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
        self._movement_actions: tuple[str, ...] = ("move_n", "move_s", "move_w", "move_e")
        self._move_repeat_initial_ms: dict[str, int | None] = {action: None for action in self._movement_actions}
        self._move_repeat_last_ms: dict[str, int | None] = {action: None for action in self._movement_actions}
        self._move_repeat_delay_ms = 420
        self._move_repeat_interval_ms = 75
        self._spellbook_repeat_actions: tuple[str, ...] = ("move_n", "move_s")
        self._spellbook_repeat_keys: dict[str, tuple[int, ...]] = {
            "move_n": (pygame.K_UP, pygame.K_w),
            "move_s": (pygame.K_DOWN, pygame.K_s),
        }
        self._spellbook_repeat_initial_ms: dict[str, int | None] = {
            action: None for action in self._spellbook_repeat_actions
        }
        self._spellbook_repeat_last_ms: dict[str, int | None] = {
            action: None for action in self._spellbook_repeat_actions
        }
        self._spellbook_repeat_delay_ms = 420
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
                    if action in self._movement_actions and getattr(pg_event, "repeat", 0):
                        continue
                    events.append(EngineEvent(EngineEventType.ACTION, {"action": action}))
            elif pg_event.type == pygame.KEYUP:
                for action, keys in self._spellbook_repeat_keys.items():
                    if pg_event.key in keys:
                        self._reset_spellbook_repeat_action(action)
                action = self.keymap.action_for_key(pg_event.key)
                if action in self._movement_actions:
                    self._reset_movement_repeat(action)
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
        self._append_movement_repeat(session, events)
        self._append_spellbook_repeat(session, events)
        return events

    def _append_movement_repeat(self, session: GameSession, events: list[EngineEvent]) -> None:
        if not self._movement_repeat_enabled(session):
            self._reset_all_movement_repeat()
            return
        pressed = pygame.key.get_pressed()
        now_ms = pygame.time.get_ticks()
        for action in self._movement_actions:
            keys = self.keymap.bindings.get(action, [])
            is_pressed = any(bool(pressed[key]) for key in keys)
            if not is_pressed:
                self._reset_movement_repeat(action)
                continue
            if self._move_repeat_initial_ms[action] is None:
                self._move_repeat_initial_ms[action] = now_ms
                self._move_repeat_last_ms[action] = None
                continue
            initial_ms = self._move_repeat_initial_ms[action]
            if initial_ms is None or now_ms - initial_ms < self._move_repeat_delay_ms:
                continue
            last_ms = self._move_repeat_last_ms[action]
            if last_ms is None or now_ms - last_ms >= self._move_repeat_interval_ms:
                events.append(EngineEvent(EngineEventType.ACTION, {"action": action}))
                self._move_repeat_last_ms[action] = now_ms

    def _movement_repeat_enabled(self, session: GameSession) -> bool:
        return not (
            session.show_main_menu
            or session.show_options_menu
            or session.show_save_load_menu
            or session.show_reagents_menu
            or session.show_spellbook_menu
            or session.targeting_action is not None
        )

    def _reset_movement_repeat(self, action: str) -> None:
        if action not in self._move_repeat_initial_ms:
            return
        self._move_repeat_initial_ms[action] = None
        self._move_repeat_last_ms[action] = None

    def _reset_all_movement_repeat(self) -> None:
        for action in self._movement_actions:
            self._reset_movement_repeat(action)

    def _append_spellbook_repeat(self, session: GameSession, events: list[EngineEvent]) -> None:
        if not session.show_spellbook_menu:
            self._reset_spellbook_repeat()
            return
        keys = pygame.key.get_pressed()

        now_ms = pygame.time.get_ticks()
        for action in self._spellbook_repeat_actions:
            action_keys = self._spellbook_repeat_keys[action]
            pressed = any(bool(keys[key]) for key in action_keys)
            if not pressed:
                self._reset_spellbook_repeat_action(action)
                continue
            if self._spellbook_repeat_initial_ms[action] is None:
                self._spellbook_repeat_initial_ms[action] = now_ms
                self._spellbook_repeat_last_ms[action] = None
                continue
            initial_ms = self._spellbook_repeat_initial_ms[action]
            if initial_ms is None or now_ms - initial_ms < self._spellbook_repeat_delay_ms:
                continue
            last_ms = self._spellbook_repeat_last_ms[action]
            if last_ms is None or now_ms - last_ms >= self._spellbook_repeat_interval_ms:
                events.append(EngineEvent(EngineEventType.ACTION, {"action": action}))
                self._spellbook_repeat_last_ms[action] = now_ms

    def _reset_spellbook_repeat_action(self, action: str) -> None:
        if action not in self._spellbook_repeat_initial_ms:
            return
        self._spellbook_repeat_initial_ms[action] = None
        self._spellbook_repeat_last_ms[action] = None

    def _reset_spellbook_repeat(self) -> None:
        for action in self._spellbook_repeat_actions:
            self._reset_spellbook_repeat_action(action)
