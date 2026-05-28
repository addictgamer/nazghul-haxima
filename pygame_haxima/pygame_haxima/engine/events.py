from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pygame


class EngineEventType(StrEnum):
    QUIT = "quit"
    ACTION = "action"
    MOUSE_TILE = "mouse_tile"
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVE = "mouse_move"
    MOUSE_WHEEL = "mouse_wheel"
    ANIMATION_TICK = "animation_tick"


@dataclass
class EngineEvent:
    kind: EngineEventType
    payload: dict


ANIMATION_EVENT = pygame.USEREVENT + 11


class EventBus:
    def __init__(self) -> None:
        self.events: list[EngineEvent] = []

    def clear(self) -> None:
        self.events.clear()

    def push(self, event: EngineEvent) -> None:
        self.events.append(event)
