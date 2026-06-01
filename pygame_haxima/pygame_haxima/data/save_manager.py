from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from pygame_haxima.domain.models import CombatState, Entity, GameSession, Item, Mode, TileField
from pygame_haxima.engine.spells import known_spell_ids

CURRENT_SAVE_VERSION = 1
SAVE_SLOT_COUNT = 6


class SaveManager:
    def __init__(self, save_dir: Path) -> None:
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.default_path = self.save_dir / "slot1-save.json"
        self.last_error: str | None = None

    def save(self, session: GameSession) -> Path:
        return self.save_slot(0, session)

    def save_slot(self, slot_index: int, session: GameSession) -> Path:
        path = self._slot_path(slot_index)
        payload = {
            "save_version": CURRENT_SAVE_VERSION,
            "party": {
                "x": session.party.x,
                "y": session.party.y,
                "gold": session.party.gold,
                "food": session.party.food,
                "turn_count": session.party.turn_count,
                "inventory": [asdict(item) for item in session.party.inventory],
                "members": [asdict(member) for member in session.party.members],
                "reagents": dict(session.party.reagents),
                "spells_known": list(session.party.spells_known),
                "selected_spell": session.party.selected_spell,
                "ward_charges": session.party.ward_charges,
            },
            "mode": session.mode.value,
            "victory": session.victory,
            "clock_hours": session.clock_hours,
            "clock_minutes": session.clock_minutes,
            "log_lines": session.log_lines[-30:],
            "settings": {
                "option_scale": session.option_scale,
                "option_fullscreen": session.option_fullscreen,
                "debug_terrain_ids": session.debug_terrain_ids,
                "debug_sprite_warnings": session.debug_sprite_warnings,
                "debug_runtime_state": session.debug_runtime_state,
                "camera_deadzone_tiles": session.camera_deadzone_tiles,
            },
            "target_cursor": list(session.target_cursor) if session.target_cursor else None,
            "targeting_action": session.targeting_action,
            "selected_npc_id": session.selected_npc_id,
            "dialogue_speaker": session.dialogue_speaker,
            "dialogue_lines": list(session.dialogue_lines),
            "npc_states": session.npc_states,
            "quest_flags": session.quest_flags,
            "combat": {
                "active": session.combat.active,
                "message": session.combat.message,
                "enemy_ids": list(session.combat.enemy_ids),
            },
            "chests": [
                {
                    "chest_id": chest.chest_id,
                    "opened": chest.opened,
                    "items": [asdict(item) for item in chest.items],
                }
                for chest in session.place.chests
            ],
            "npcs": [
                {
                    "npc_id": npc.npc_id,
                    "x": npc.x,
                    "y": npc.y,
                }
                for npc in session.place.npcs
            ],
            "monsters": [asdict(monster) for monster in session.place.monsters],
            "ground_items": {
                f"{x},{y}": [asdict(item) for item in items]
                for (x, y), items in session.place.ground_items.items()
            },
            "tile_fields": [
                {
                    "x": tile_field.x,
                    "y": tile_field.y,
                    "field_kind": tile_field.field_kind,
                    "turns_remaining": tile_field.turns_remaining,
                }
                for tile_field in session.place.tile_fields.values()
            ],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def load(self, session: GameSession) -> bool:
        return self.load_slot(0, session)

    def load_slot(self, slot_index: int, session: GameSession) -> bool:
        self.last_error = None
        path = self._slot_path(slot_index)
        if not path.exists():
            self.last_error = "no_save"
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self.last_error = "corrupt_save"
            self._quarantine_corrupt_save(path)
            return False

        try:
            payload = self._migrate_payload(payload)
            party_payload = payload["party"]
            members_payload = party_payload.get("members", [])
            if members_payload:
                session.party.members = [Entity(**member) for member in members_payload]
            session.party.x = party_payload["x"]
            session.party.y = party_payload["y"]
            session.party.gold = party_payload["gold"]
            session.party.food = party_payload["food"]
            session.party.turn_count = party_payload["turn_count"]
            session.party.inventory = [Item(**item) for item in party_payload.get("inventory", [])]
            reagents_payload = party_payload.get("reagents", {})
            if isinstance(reagents_payload, dict):
                cleaned: dict[str, int] = {}
                for key, value in reagents_payload.items():
                    if isinstance(key, str) and isinstance(value, int):
                        cleaned[key] = max(0, value)
                if cleaned:
                    session.party.reagents = cleaned
            spells_known_payload = party_payload.get("spells_known", [])
            if isinstance(spells_known_payload, list):
                known = [spell for spell in spells_known_payload if isinstance(spell, str)]
                if known:
                    session.party.spells_known = known
            selected_spell = party_payload.get("selected_spell", session.party.selected_spell)
            if isinstance(selected_spell, str):
                session.party.selected_spell = selected_spell
            ward_charges = party_payload.get("ward_charges", session.party.ward_charges)
            if isinstance(ward_charges, int):
                session.party.ward_charges = max(0, min(6, ward_charges))
            if session.party.members:
                session.party.members[0].x = session.party.x
                session.party.members[0].y = session.party.y
            session.mode = Mode(payload["mode"])
            session.victory = bool(payload.get("victory", False))
            session.clock_hours = payload["clock_hours"]
            session.clock_minutes = payload["clock_minutes"]
            session.log_lines = payload["log_lines"]
            settings_payload = payload.get("settings", {})
            if isinstance(settings_payload, dict):
                scale = settings_payload.get("option_scale", session.option_scale)
                if isinstance(scale, int):
                    session.option_scale = max(1, min(4, scale))
                session.option_fullscreen = bool(
                    settings_payload.get("option_fullscreen", session.option_fullscreen)
                )
                session.debug_terrain_ids = bool(
                    settings_payload.get("debug_terrain_ids", session.debug_terrain_ids)
                )
                session.debug_sprite_warnings = bool(
                    settings_payload.get("debug_sprite_warnings", session.debug_sprite_warnings)
                )
                session.debug_runtime_state = bool(
                    settings_payload.get("debug_runtime_state", session.debug_runtime_state)
                )
                deadzone = settings_payload.get("camera_deadzone_tiles", session.camera_deadzone_tiles)
                if isinstance(deadzone, int):
                    session.camera_deadzone_tiles = max(1, min(12, deadzone))
            target_cursor = payload.get("target_cursor")
            if isinstance(target_cursor, list) and len(target_cursor) == 2:
                session.target_cursor = (int(target_cursor[0]), int(target_cursor[1]))
            else:
                session.target_cursor = None
            session.targeting_action = payload.get("targeting_action")
            if session.targeting_action is not None and not isinstance(session.targeting_action, str):
                session.targeting_action = None
            selected_npc_id = payload.get("selected_npc_id")
            session.selected_npc_id = selected_npc_id if isinstance(selected_npc_id, str) else None
            dialogue_speaker = payload.get("dialogue_speaker")
            session.dialogue_speaker = dialogue_speaker if isinstance(dialogue_speaker, str) else None
            dialogue_lines = payload.get("dialogue_lines", [])
            if isinstance(dialogue_lines, list):
                session.dialogue_lines = [line for line in dialogue_lines if isinstance(line, str)]
            else:
                session.dialogue_lines = []
            npc_states = payload.get("npc_states", {})
            session.npc_states = self._sanitize_nested_state(npc_states)
            quest_flags = payload.get("quest_flags", {})
            session.quest_flags = self._sanitize_flat_state(quest_flags)
            combat_payload = payload.get("combat", {})
            session.combat = self._sanitize_combat_state(combat_payload)
            chests_by_id = {ch.chest_id: ch for ch in session.place.chests}
            for chest_payload in payload.get("chests", []):
                chest = chests_by_id.get(chest_payload["chest_id"])
                if chest is None:
                    continue
                chest.opened = chest_payload["opened"]
                chest.items = [Item(**item) for item in chest_payload.get("items", [])]
            npcs_by_id = {n.npc_id: n for n in session.place.npcs}
            for npc_payload in payload.get("npcs", []):
                if not isinstance(npc_payload, dict):
                    continue
                npc = npcs_by_id.get(npc_payload.get("npc_id"))
                if npc is None:
                    continue
                x = npc_payload.get("x", npc.x)
                y = npc_payload.get("y", npc.y)
                if isinstance(x, int) and isinstance(y, int) and session.place.in_bounds(x, y):
                    npc.x = x
                    npc.y = y
            monsters_by_id = {m.entity_id: m for m in session.place.monsters}
            for monster_payload in payload.get("monsters", []):
                monster = monsters_by_id.get(monster_payload["entity_id"])
                if monster is None:
                    continue
                monster.hp = monster_payload["hp"]
                monster.x = monster_payload["x"]
                monster.y = monster_payload["y"]
                facing = monster_payload.get("facing")
                if isinstance(facing, str) and facing in {"n", "s", "e", "w"}:
                    monster.facing = facing

            ground_payload = payload.get("ground_items", {})
            session.place.ground_items.clear()
            if isinstance(ground_payload, dict):
                for key, items in ground_payload.items():
                    if not isinstance(key, str) or "," not in key:
                        continue
                    x_str, y_str = key.split(",", maxsplit=1)
                    try:
                        xy = (int(x_str), int(y_str))
                    except ValueError:
                        continue
                    if not isinstance(items, list):
                        continue
                    session.place.ground_items[xy] = [Item(**item) for item in items if isinstance(item, dict)]
            session.place.tile_fields.clear()
            for field_payload in payload.get("tile_fields", []):
                if not isinstance(field_payload, dict):
                    continue
                x = field_payload.get("x")
                y = field_payload.get("y")
                field_kind = field_payload.get("field_kind")
                turns = field_payload.get("turns_remaining")
                if (
                    isinstance(x, int)
                    and isinstance(y, int)
                    and isinstance(field_kind, str)
                    and isinstance(turns, int)
                    and session.place.in_bounds(x, y)
                    and turns > 0
                ):
                    session.place.tile_fields[(x, y)] = TileField(
                        x=x, y=y, field_kind=field_kind, turns_remaining=turns
                    )
            self._normalize_loaded_session(session)
            return True
        except (KeyError, TypeError, ValueError):
            self.last_error = "invalid_schema"
            return False

    def list_slots(self) -> list[str]:
        labels: list[str] = []
        for idx in range(SAVE_SLOT_COUNT):
            path = self._slot_path(idx)
            slot_name = f"Slot {idx + 1}"
            if not path.exists():
                labels.append(f"{slot_name}: (empty)")
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                turn = payload.get("party", {}).get("turn_count", "?")
                hour = payload.get("clock_hours", "?")
                minute = payload.get("clock_minutes", "?")
                if isinstance(hour, int) and isinstance(minute, int):
                    time_text = f"{hour:02d}:{minute:02d}"
                else:
                    time_text = "--:--"
                labels.append(f"{slot_name}: Turn {turn}, {time_text}")
            except Exception:
                labels.append(f"{slot_name}: (corrupt)")
        return labels

    def _migrate_payload(self, payload: dict[str, object]) -> dict[str, object]:
        version = int(payload.get("save_version", 0))
        migrated = dict(payload)
        while version < CURRENT_SAVE_VERSION:
            if version == 0:
                migrated = self._migrate_v0_to_v1(migrated)
                version = 1
                continue
            break
        migrated["save_version"] = version
        return migrated

    def _migrate_v0_to_v1(self, payload: dict[str, object]) -> dict[str, object]:
        migrated = dict(payload)
        migrated.setdefault("ground_items", {})
        migrated.setdefault("victory", False)
        migrated.setdefault("target_cursor", None)
        migrated.setdefault("targeting_action", None)
        migrated.setdefault("selected_npc_id", None)
        migrated.setdefault("dialogue_speaker", None)
        migrated.setdefault("dialogue_lines", [])
        migrated.setdefault("npc_states", {})
        migrated.setdefault("quest_flags", {})
        migrated.setdefault("combat", {"active": False, "message": "", "enemy_ids": []})
        migrated.setdefault("npcs", [])
        migrated.setdefault(
            "settings",
            {
                "option_scale": 1,
                "option_fullscreen": False,
                "debug_terrain_ids": False,
                "debug_sprite_warnings": False,
                "debug_runtime_state": False,
                "camera_deadzone_tiles": 4,
            },
        )
        party = migrated.get("party")
        if isinstance(party, dict):
            default_spells = known_spell_ids()
            party.setdefault("members", [])
            party.setdefault("inventory", [])
            party.setdefault("reagents", {"sulphurous_ash": 2, "ginseng": 1, "garlic": 1})
            party.setdefault("spells_known", default_spells)
            if "spark" in default_spells:
                party.setdefault("selected_spell", "spark")
            elif default_spells:
                party.setdefault("selected_spell", default_spells[0])
            else:
                party.setdefault("selected_spell", "spark")
            party.setdefault("ward_charges", 0)
        migrated.setdefault("log_lines", [])
        return migrated

    def _quarantine_corrupt_save(self, path: Path) -> None:
        try:
            bad_path = path.with_suffix(".corrupt.json")
            path.replace(bad_path)
        except OSError:
            # Keep failure silent; load() caller already gets False.
            pass

    def _slot_path(self, slot_index: int) -> Path:
        clamped = max(0, min(SAVE_SLOT_COUNT - 1, slot_index))
        return self.save_dir / f"slot{clamped + 1}-save.json"

    def _normalize_loaded_session(self, session: GameSession) -> None:
        # Normalize transient runtime/UI state for deterministic post-load behavior.
        session.show_options_menu = False
        session.show_save_load_menu = False
        session.show_reagents_menu = False
        session.show_spellbook_menu = False
        session.spellbook_tab = "all"
        session.spellbook_selected_index = 0
        session.spellbook_hover_index = None
        session.save_load_mode = None
        session.save_load_selected_slot = 0
        session.target_cursor = None
        session.targeting_action = None
        session.selected_npc_id = None
        session.command_prompt = "Command> (H help, F10 options)"
        session.combat_feedback_text = None
        session.combat_feedback_ticks = 0
        session.combat_feedback_world_pos = None
        session.combat_feedback_lines = []
        session.camera_start_x = None
        session.camera_start_y = None
        available = known_spell_ids()
        available_set = set(available)
        session.party.spells_known = [spell for spell in session.party.spells_known if spell in available_set] or available
        if session.party.selected_spell not in session.party.spells_known:
            session.party.selected_spell = session.party.spells_known[0] if session.party.spells_known else "spark"

        living_enemy_ids = {monster.entity_id for monster in session.place.monsters if monster.is_alive()}
        filtered_enemy_ids = [eid for eid in session.combat.enemy_ids if eid in living_enemy_ids]
        session.combat.enemy_ids = filtered_enemy_ids
        if not filtered_enemy_ids:
            session.combat.active = False
            session.combat.message = ""
        if session.mode == Mode.COMBAT and not session.combat.active:
            session.mode = Mode.EXPLORE
        if session.mode != Mode.COMBAT and session.combat.active:
            session.mode = Mode.COMBAT

    def _sanitize_flat_state(self, value: object) -> dict[str, object]:
        if not isinstance(value, dict):
            return {}
        out: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            if isinstance(item, (str, int, float, bool)) or item is None:
                out[key] = item
        return out

    def _sanitize_nested_state(self, value: object) -> dict[str, dict[str, object]]:
        if not isinstance(value, dict):
            return {}
        out: dict[str, dict[str, object]] = {}
        for key, state in value.items():
            if not isinstance(key, str):
                continue
            out[key] = self._sanitize_flat_state(state)
        return out

    def _sanitize_combat_state(self, value: object) -> CombatState:
        if not isinstance(value, dict):
            return CombatState()
        active = bool(value.get("active", False))
        message_raw = value.get("message", "")
        message = message_raw if isinstance(message_raw, str) else ""
        enemy_ids_raw = value.get("enemy_ids", [])
        enemy_ids: list[str] = []
        if isinstance(enemy_ids_raw, list):
            enemy_ids = [eid for eid in enemy_ids_raw if isinstance(eid, str)]
        return CombatState(active=active, message=message, enemy_ids=enemy_ids)
