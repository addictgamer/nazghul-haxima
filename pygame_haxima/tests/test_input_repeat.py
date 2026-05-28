from __future__ import annotations

import pygame

from pygame_haxima.data.content_registry import ContentRegistry
from pygame_haxima.engine.events import EngineEventType
from pygame_haxima.engine.input import InputController
from pygame_haxima.engine.keymap import KeyMap


class _StubRenderer:
    def window_to_virtual(self, pos: tuple[int, int]) -> tuple[int, int]:
        return pos

    def screen_to_map_tile(self, pos: tuple[int, int], _session: object) -> tuple[int, int] | None:
        return pos


class _PressedKeys:
    def __init__(self, pressed_keys: set[int]) -> None:
        self._pressed_keys = pressed_keys

    def __getitem__(self, key: int) -> int:
        return 1 if key in self._pressed_keys else 0


def test_hold_w_repeats_move_after_delay(monkeypatch) -> None:
    session = ContentRegistry().make_new_session()
    controller = InputController(KeyMap(), _StubRenderer())  # type: ignore[arg-type]

    now_ms = {"value": 0}
    monkeypatch.setattr("pygame.event.get", lambda: [])
    monkeypatch.setattr("pygame.time.get_ticks", lambda: now_ms["value"])
    monkeypatch.setattr("pygame.key.get_pressed", lambda: _PressedKeys({pygame.K_w}))

    assert controller.poll(session) == []

    now_ms["value"] = 120
    assert controller.poll(session) == []

    now_ms["value"] = 400
    assert controller.poll(session) == []

    now_ms["value"] = 430
    events = controller.poll(session)
    assert len(events) == 1
    assert events[0].kind == EngineEventType.ACTION
    assert events[0].payload["action"] == "move_n"

    now_ms["value"] = 510
    events = controller.poll(session)
    assert len(events) == 1
    assert events[0].kind == EngineEventType.ACTION
    assert events[0].payload["action"] == "move_n"


def test_hold_w_does_not_repeat_while_menu_open(monkeypatch) -> None:
    session = ContentRegistry().make_new_session()
    session.show_spellbook_menu = True
    controller = InputController(KeyMap(), _StubRenderer())  # type: ignore[arg-type]

    monkeypatch.setattr("pygame.event.get", lambda: [])
    monkeypatch.setattr("pygame.time.get_ticks", lambda: 500)
    monkeypatch.setattr("pygame.key.get_pressed", lambda: _PressedKeys({pygame.K_w}))

    assert controller.poll(session) == []


def test_spellbook_down_repeats_after_spellbook_delay(monkeypatch) -> None:
    session = ContentRegistry().make_new_session()
    session.show_spellbook_menu = True
    controller = InputController(KeyMap(), _StubRenderer())  # type: ignore[arg-type]

    now_ms = {"value": 0}
    monkeypatch.setattr("pygame.event.get", lambda: [])
    monkeypatch.setattr("pygame.time.get_ticks", lambda: now_ms["value"])
    monkeypatch.setattr("pygame.key.get_pressed", lambda: _PressedKeys({pygame.K_DOWN}))

    assert controller.poll(session) == []

    now_ms["value"] = 400
    assert controller.poll(session) == []

    now_ms["value"] = 430
    events = controller.poll(session)
    assert len(events) == 1
    assert events[0].kind == EngineEventType.ACTION
    assert events[0].payload["action"] == "move_s"


def test_spellbook_s_repeats_after_spellbook_delay(monkeypatch) -> None:
    session = ContentRegistry().make_new_session()
    session.show_spellbook_menu = True
    controller = InputController(KeyMap(), _StubRenderer())  # type: ignore[arg-type]

    now_ms = {"value": 0}
    monkeypatch.setattr("pygame.event.get", lambda: [])
    monkeypatch.setattr("pygame.time.get_ticks", lambda: now_ms["value"])
    monkeypatch.setattr("pygame.key.get_pressed", lambda: _PressedKeys({pygame.K_s}))

    assert controller.poll(session) == []

    now_ms["value"] = 410
    assert controller.poll(session) == []

    now_ms["value"] = 430
    events = controller.poll(session)
    assert len(events) == 1
    assert events[0].kind == EngineEventType.ACTION
    assert events[0].payload["action"] == "move_s"


def test_spellbook_up_repeats_after_spellbook_delay(monkeypatch) -> None:
    session = ContentRegistry().make_new_session()
    session.show_spellbook_menu = True
    controller = InputController(KeyMap(), _StubRenderer())  # type: ignore[arg-type]

    now_ms = {"value": 0}
    monkeypatch.setattr("pygame.event.get", lambda: [])
    monkeypatch.setattr("pygame.time.get_ticks", lambda: now_ms["value"])
    monkeypatch.setattr("pygame.key.get_pressed", lambda: _PressedKeys({pygame.K_UP}))

    assert controller.poll(session) == []

    now_ms["value"] = 410
    assert controller.poll(session) == []

    now_ms["value"] = 430
    events = controller.poll(session)
    assert len(events) == 1
    assert events[0].kind == EngineEventType.ACTION
    assert events[0].payload["action"] == "move_n"


def test_spellbook_w_repeats_after_spellbook_delay(monkeypatch) -> None:
    session = ContentRegistry().make_new_session()
    session.show_spellbook_menu = True
    controller = InputController(KeyMap(), _StubRenderer())  # type: ignore[arg-type]

    now_ms = {"value": 0}
    monkeypatch.setattr("pygame.event.get", lambda: [])
    monkeypatch.setattr("pygame.time.get_ticks", lambda: now_ms["value"])
    monkeypatch.setattr("pygame.key.get_pressed", lambda: _PressedKeys({pygame.K_w}))

    assert controller.poll(session) == []

    now_ms["value"] = 410
    assert controller.poll(session) == []

    now_ms["value"] = 430
    events = controller.poll(session)
    assert len(events) == 1
    assert events[0].kind == EngineEventType.ACTION
    assert events[0].payload["action"] == "move_n"
