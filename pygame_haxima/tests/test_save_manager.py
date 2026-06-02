from __future__ import annotations

import json

from pygame_haxima.data.content_registry import ContentRegistry
from pygame_haxima.data.save_manager import SaveManager
from pygame_haxima.domain.models import CombatState, Item, Mode


def test_save_load_round_trip_persists_runtime_state(tmp_path) -> None:
    manager = SaveManager(tmp_path / "saves")
    session = ContentRegistry().make_new_session()

    # Mutate representative runtime state before saving.
    session.party.x = 10
    session.party.y = 8
    session.party.members[0].x = 10
    session.party.members[0].y = 8
    session.party.inventory.append(Item("t_dagger", "Dagger", 8, sprite_key="s_dagger"))
    session.clock_hours = 13
    session.clock_minutes = 45
    session.option_scale = 2
    session.option_fullscreen = True
    session.debug_runtime_state = True
    session.camera_deadzone_tiles = 6
    session.quest_flags["opened:starter_chest"] = True
    session.npc_states["mentor"] = {"talk_count": 2, "last_turn": 5}
    session.combat = CombatState(active=True, message="Engaged Wolf", enemy_ids=["wolf_1"])
    session.place.npcs[0].x = 11
    session.place.npcs[0].y = 8
    session.place.ground_items[(5, 11)] = [Item("t_heal_potion", "Healing Potion", 18)]
    session.party.reagents["sulphurous_ash"] = 7
    session.party.spells_known = ["spark", "heal"]
    session.party.selected_spell = "heal"
    session.party.ward_charges = 2

    manager.save_slot(1, session)

    loaded = ContentRegistry().make_new_session()
    assert manager.load_slot(1, loaded) is True

    assert loaded.party.x == 10
    assert loaded.party.y == 8
    assert loaded.party.inventory[-1].item_id == "t_dagger"
    assert loaded.clock_hours == 13
    assert loaded.clock_minutes == 45
    assert loaded.option_scale == 2
    assert loaded.option_fullscreen is True
    assert loaded.debug_runtime_state is True
    assert loaded.camera_deadzone_tiles == 6
    assert loaded.quest_flags["opened:starter_chest"] is True
    assert loaded.npc_states["mentor"]["talk_count"] == 2
    assert loaded.place.npcs[0].x == 11
    assert loaded.place.npcs[0].y == 8
    assert loaded.place.ground_items[(5, 11)][0].item_id == "t_heal_potion"
    assert loaded.party.reagents["sulphurous_ash"] == 7
    assert loaded.party.spells_known == ["spark", "heal"]
    assert loaded.party.selected_spell == "heal"
    assert loaded.party.ward_charges == 2
    # Combat state should deterministically restore when living enemies still match saved enemy_ids.
    assert loaded.mode == Mode.COMBAT
    assert loaded.combat.active is True
    assert loaded.combat.enemy_ids == ["wolf_1"]


def test_load_rebuilds_cloviskeep_from_saved_place_id(tmp_path) -> None:
    registry = ContentRegistry()
    manager = SaveManager(tmp_path / "saves", content_registry=registry)
    session = registry.make_new_session("cloviskeep")
    session.party.x = 12
    session.party.y = 14
    session.party.members[0].x = 12
    session.party.members[0].y = 14
    if session.place.monsters:
        session.place.monsters[0].hp = 3
    manager.save_slot(4, session)

    loaded = registry.make_new_session("tutorial")
    assert loaded.place.place_id == "tutorial_wilderness"
    assert manager.load_slot(4, loaded) is True
    assert loaded.place.place_id == "p_cloviskeep"
    assert loaded.party.x == 12
    assert loaded.party.y == 14


def test_load_corrupt_slot_quarantines_file(tmp_path) -> None:
    manager = SaveManager(tmp_path / "saves")
    slot_path = tmp_path / "saves" / "slot1-save.json"
    slot_path.parent.mkdir(parents=True, exist_ok=True)
    slot_path.write_text("{this is not valid json", encoding="utf-8")

    session = ContentRegistry().make_new_session()
    assert manager.load_slot(0, session) is False

    assert (tmp_path / "saves" / "slot1-save.corrupt.json").exists()


def test_load_v0_payload_migrates_with_defaults(tmp_path) -> None:
    manager = SaveManager(tmp_path / "saves")
    session = ContentRegistry().make_new_session()
    manager.save_slot(2, session)

    slot_path = tmp_path / "saves" / "slot3-save.json"
    payload = json.loads(slot_path.read_text(encoding="utf-8"))
    payload.pop("save_version", None)
    payload.pop("settings", None)
    payload.pop("npcs", None)
    slot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    loaded = ContentRegistry().make_new_session()
    loaded.option_scale = 4
    loaded.camera_deadzone_tiles = 9
    assert manager.load_slot(2, loaded) is True

    # V0 payload should migrate and default missing fields safely.
    assert loaded.option_scale == 1
    assert loaded.option_fullscreen is False
    assert loaded.camera_deadzone_tiles == 4
    assert loaded.party.reagents.get("sulphurous_ash") == 2
    assert loaded.party.selected_spell == "spark"
