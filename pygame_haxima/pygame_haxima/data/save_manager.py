from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from pygame_haxima.domain.models import Entity, GameSession, Item, Mode

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
            },
            "mode": session.mode.value,
            "victory": session.victory,
            "clock_hours": session.clock_hours,
            "clock_minutes": session.clock_minutes,
            "log_lines": session.log_lines[-30:],
            "target_cursor": list(session.target_cursor) if session.target_cursor else None,
            "targeting_action": session.targeting_action,
            "selected_npc_id": session.selected_npc_id,
            "dialogue_speaker": session.dialogue_speaker,
            "dialogue_lines": list(session.dialogue_lines),
            "chests": [
                {
                    "chest_id": chest.chest_id,
                    "opened": chest.opened,
                    "items": [asdict(item) for item in chest.items],
                }
                for chest in session.place.chests
            ],
            "monsters": [asdict(monster) for monster in session.place.monsters],
            "ground_items": {
                f"{x},{y}": [asdict(item) for item in items]
                for (x, y), items in session.place.ground_items.items()
            },
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
            if session.party.members:
                session.party.members[0].x = session.party.x
                session.party.members[0].y = session.party.y
            session.mode = Mode(payload["mode"])
            session.victory = bool(payload.get("victory", False))
            session.clock_hours = payload["clock_hours"]
            session.clock_minutes = payload["clock_minutes"]
            session.log_lines = payload["log_lines"]
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
            chests_by_id = {ch.chest_id: ch for ch in session.place.chests}
            for chest_payload in payload.get("chests", []):
                chest = chests_by_id.get(chest_payload["chest_id"])
                if chest is None:
                    continue
                chest.opened = chest_payload["opened"]
                chest.items = [Item(**item) for item in chest_payload.get("items", [])]
            monsters_by_id = {m.entity_id: m for m in session.place.monsters}
            for monster_payload in payload.get("monsters", []):
                monster = monsters_by_id.get(monster_payload["entity_id"])
                if monster is None:
                    continue
                monster.hp = monster_payload["hp"]
                monster.x = monster_payload["x"]
                monster.y = monster_payload["y"]

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
        party = migrated.get("party")
        if isinstance(party, dict):
            party.setdefault("members", [])
            party.setdefault("inventory", [])
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
        session.save_load_mode = None
        session.save_load_selected_slot = 0
        session.target_cursor = None
        session.targeting_action = None
        session.selected_npc_id = None
        session.command_prompt = "Command> (H help, F10 options)"
        session.combat_feedback_text = None
        session.combat_feedback_ticks = 0
        session.combat_feedback_world_pos = None
        session.camera_start_x = None
        session.camera_start_y = None

        if not any(monster.is_alive() for monster in session.place.monsters) and session.mode == Mode.COMBAT:
            session.mode = Mode.EXPLORE
