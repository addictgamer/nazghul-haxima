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
    assert session.combat_feedback_text is not None
    assert "you: hit" in session.combat_feedback_text.lower()
    assert "wolf: falls" in session.combat_feedback_text.lower()


def test_cast_spark_consumes_reagent_and_damages_target(tmp_path, monkeypatch) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.x = 12
    session.party.y = 9
    session.party.members[0].x = 12
    session.party.members[0].y = 9
    wolf = session.place.monsters[0]
    wolf.hp = 9
    session.party.reagents["sulphurous_ash"] = 2
    monkeypatch.setattr("pygame_haxima.engine.loop.random.randint", lambda _a, _b: 4)

    loop.process_events(session, [_action("cast"), _action("confirm")])

    assert wolf.hp == 5
    assert session.party.reagents["sulphurous_ash"] == 1
    assert session.party.turn_count == 1
    assert session.combat_feedback_text is not None
    assert "spark 4" in session.combat_feedback_text.lower()


def test_cast_spark_requires_reagent(tmp_path) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.x = 12
    session.party.y = 9
    session.party.members[0].x = 12
    session.party.members[0].y = 9
    session.party.reagents["sulphurous_ash"] = 0

    loop.process_events(session, [_action("cast")])

    assert session.targeting_action is None
    assert "lack reagents for spark" in session.log_lines[-1].lower()


def test_cycle_spell_rotates_known_spells(tmp_path) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.spells_known = ["spark", "heal", "ward"]
    session.party.selected_spell = "spark"

    loop.process_events(session, [_action("cycle_spell")])
    assert session.party.selected_spell == "heal"

    loop.process_events(session, [_action("cycle_spell")])
    assert session.party.selected_spell == "ward"

    loop.process_events(session, [_action("cycle_spell")])
    assert session.party.selected_spell == "spark"


def test_cast_heal_consumes_ginseng_and_restores_hp(tmp_path, monkeypatch) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.selected_spell = "heal"
    session.party.lead().hp = 12
    session.party.reagents["ginseng"] = 1
    monkeypatch.setattr("pygame_haxima.engine.loop.random.randint", lambda _a, _b: 5)

    loop.process_events(session, [_action("cast")])

    assert session.party.lead().hp == 17
    assert session.party.reagents["ginseng"] == 0
    assert session.party.turn_count == 1
    assert session.combat_feedback_text is not None
    assert "heal 5" in session.combat_feedback_text.lower()


def test_cast_ward_reduces_next_enemy_hit(tmp_path, monkeypatch) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.x = 13
    session.party.y = 9
    session.party.members[0].x = 13
    session.party.members[0].y = 9
    session.party.selected_spell = "ward"
    session.party.reagents["garlic"] = 1

    # Counterattack roll: hit for base 6, reduced by ward to 4.
    rolls = iter([6, 1])
    monkeypatch.setattr("pygame_haxima.engine.loop.random.randint", lambda _a, _b: next(rolls))

    loop.process_events(session, [_action("cast")])

    assert session.party.reagents["garlic"] == 0
    assert session.party.lead().hp == 16
    assert session.party.ward_charges == 1
    assert session.party.turn_count == 1


def test_reagents_modal_toggle_updates_prompt(tmp_path) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()

    loop.process_events(session, [_action("reagents_menu")])
    assert session.show_reagents_menu is True
    assert "Reagents>" in session.command_prompt

    loop.process_events(session, [_action("reagents_menu")])
    assert session.show_reagents_menu is False
    assert session.command_prompt == "Command> (H help, F10 options)"


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


def test_party_facing_updates_with_movement_direction(tmp_path) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()

    loop.process_events(session, [_action("move_e")])
    assert session.party.lead().facing == "e"

    loop.process_events(session, [_action("move_w")])
    assert session.party.lead().facing == "w"

    loop.process_events(session, [_action("move_s")])
    assert session.party.lead().facing == "s"

    loop.process_events(session, [_action("move_n")])
    assert session.party.lead().facing == "n"


def test_party_cannot_step_into_impassable_wall(tmp_path) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.x = 1
    session.party.y = 1
    session.party.members[0].x = 1
    session.party.members[0].y = 1

    loop.process_events(session, [_action("move_n")])

    assert (session.party.x, session.party.y) == (1, 1)
    assert session.party.turn_count == 0
    assert session.log_lines[-1] == "Blocked."


def test_open_action_rejects_when_no_chest_in_range(tmp_path) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()

    loop.process_events(session, [_action("open")])

    assert session.targeting_action is None
    assert session.target_cursor is None
    assert session.log_lines[-1] == "You can't perform that action right now."


def test_nonlethal_attack_round_resets_to_explore_and_advances_turn(tmp_path, monkeypatch) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.x = 13
    session.party.y = 9
    session.party.members[0].x = 13
    session.party.members[0].y = 9
    wolf = session.place.monsters[0]
    start_hp = wolf.hp
    start_party_hp = session.party.lead().hp

    # Sequence: player miss (1 vs 6), wolf miss (1 vs 6)
    rolls = iter([1, 6, 1, 6])
    monkeypatch.setattr("pygame_haxima.engine.loop.random.randint", lambda _a, _b: next(rolls))

    loop.process_events(session, [_action("attack"), _action("confirm")])

    assert wolf.hp == start_hp
    assert session.party.lead().hp == start_party_hp
    assert session.victory is False
    assert "defeated:wolf_1" not in session.quest_flags
    assert session.mode.value == "explore"
    assert session.combat.active is False
    assert session.party.turn_count == 1


def test_combat_feedback_merges_player_and_enemy_messages(tmp_path, monkeypatch) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.x = 13
    session.party.y = 9
    session.party.members[0].x = 13
    session.party.members[0].y = 9

    # Player miss, then wolf miss so feedback should render as a stacked multi-line popup.
    rolls = iter([1, 6, 1, 6])
    monkeypatch.setattr("pygame_haxima.engine.loop.random.randint", lambda _a, _b: next(rolls))

    loop.process_events(session, [_action("attack"), _action("confirm")])

    assert session.combat_feedback_text is not None
    assert "you:" in session.combat_feedback_text.lower()
    assert "wolf:" in session.combat_feedback_text.lower()
    assert "\n" in session.combat_feedback_text
    assert len(session.combat_feedback_lines) == 2


def test_new_attack_round_clears_previous_banner_text(tmp_path, monkeypatch) -> None:
    loop = _make_loop(tmp_path)
    session = ContentRegistry().make_new_session()
    session.party.x = 13
    session.party.y = 9
    session.party.members[0].x = 13
    session.party.members[0].y = 9

    # Round 1: player hit, wolf miss. Round 2: player miss, wolf hit.
    rolls = iter([6, 1, 1, 6, 1, 6, 6, 1])
    monkeypatch.setattr("pygame_haxima.engine.loop.random.randint", lambda _a, _b: next(rolls))

    loop.process_events(session, [_action("attack"), _action("confirm")])
    assert session.combat_feedback_text == "You: Hit 8\nWolf: Misses"

    loop.process_events(session, [_action("attack"), _action("confirm")])
    assert session.combat_feedback_text == "You: Miss\nWolf: Hit 6"
    assert len(session.combat_feedback_lines) == 2
