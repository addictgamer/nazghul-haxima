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
            elif pg_event.type == pygame.MOUSEBUTTONDOWN and pg_event.button == 1:
                ui_pos = self.renderer.window_to_virtual(pg_event.pos)
                events.append(EngineEvent(EngineEventType.MOUSE_CLICK, {"ui_pos": ui_pos}))
                tile = self.renderer.screen_to_map_tile(pg_event.pos, session)
                if tile is not None:
                    events.append(EngineEvent(EngineEventType.MOUSE_TILE, {"tile": tile}))
        return events
