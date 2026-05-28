from __future__ import annotations

from pathlib import Path

from pygame_haxima.data.content_registry import ContentRegistry
from pygame_haxima.data.save_manager import SaveManager
from pygame_haxima.engine.events import EngineEvent, EngineEventType
from pygame_haxima.engine.loop import TurnLoop


class _StubTextUi:
    def save_load_hit_test(self, ui_pos: tuple[int, int], session: object) -> tuple[str, int | None] | None:
        return None


class _StubRenderer:
    def __init__(self) -> None:
        self.scale = 1
        self.is_fullscreen = False
        self.text_ui = _StubTextUi()

    def toggle_fullscreen(self) -> None:
        self.is_fullscreen = not self.is_fullscreen

    def set_scale(self, scale: int) -> None:
        self.scale = scale


class _StubAudio:
    def __init__(self) -> None:
        self.effects: list[str] = []

    def play_effect(self, path: str) -> None:
        self.effects.append(path)


def _action(name: str) -> EngineEvent:
    return EngineEvent(kind=EngineEventType.ACTION, payload={"action": name})


def _make_loop(tmp_path: Path) -> TurnLoop:
    return TurnLoop(
        renderer=_StubRenderer(),  # type: ignore[arg-type]
        audio=_StubAudio(),  # type: ignore[arg-type]
        save_manager=SaveManager(tmp_path / "saves"),
    )


def test_talk_flow_updates_npc_state_and_flags(tmp_path) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.x = 6
    session.party.y = 9
    session.party.members[0].x = 6
    session.party.members[0].y = 9

    loop.process_events(session, [_action("talk")])
    assert session.targeting_action == "talk"
    assert session.target_cursor == (7, 9)

    loop.process_events(session, [_action("confirm")])

    assert session.targeting_action is None
    assert session.npc_states["mentor"]["talk_count"] == 1
    assert session.quest_flags["talked:mentor"] is True
    assert session.dialogue_speaker == "Old Mentor"
    assert len(session.dialogue_lines) == 3
    assert session.party.turn_count == 1


def test_open_then_get_items_flow(tmp_path) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.x = 5
    session.party.y = 10
    session.party.members[0].x = 5
    session.party.members[0].y = 10

    loop.process_events(session, [_action("open"), _action("confirm")])
    chest = session.place.chests[0]
    assert chest.opened is True
    assert session.quest_flags["opened:starter_chest"] is True
    assert session.place.ground_items[(5, 11)]

    loop.process_events(session, [_action("move_s"), _action("get")])
    assert session.party.y == 11
    assert {item.item_id for item in session.party.inventory} == {
        "t_dagger",
        "t_armor_leather",
        "t_heal_potion",
    }
    assert session.place.ground_items[(5, 11)] == []


def test_attack_flow_can_defeat_wolf_and_set_victory(tmp_path, monkeypatch) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.x = 13
    session.party.y = 9
    session.party.members[0].x = 13
    session.party.members[0].y = 9
    wolf = session.place.monsters[0]
    wolf.hp = 1

    rolls = iter([6, 1])
    monkeypatch.setattr("pygame_haxima.engine.loop.random.randint", lambda _a, _b: next(rolls))

    loop.process_events(session, [_action("attack"), _action("confirm")])

    assert wolf.is_alive() is False
    assert session.quest_flags["defeated:wolf_1"] is True
    assert session.victory is True
    assert session.mode.value == "explore"
    assert session.combat.active is False


def test_party_cannot_step_onto_npc_tile(tmp_path) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.x = 6
    session.party.y = 9
    session.party.members[0].x = 6
    session.party.members[0].y = 9

    loop.process_events(session, [_action("move_e")])

    assert (session.party.x, session.party.y) == (6, 9)
    assert session.log_lines[-1] == "Blocked."
