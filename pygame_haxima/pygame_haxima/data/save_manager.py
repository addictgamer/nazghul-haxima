from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from pygame_haxima.domain.models import Entity, GameSession, Item, Mode

CURRENT_SAVE_VERSION = 1


class SaveManager:
    def __init__(self, save_dir: Path) -> None:
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.default_path = self.save_dir / "tutorial-save.json"
        self.last_error: str | None = None

    def save(self, session: GameSession) -> Path:
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
        self.default_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.default_path

    def load(self, session: GameSession) -> bool:
        self.last_error = None
        if not self.default_path.exists():
            self.last_error = "no_save"
            return False
        try:
            payload = json.loads(self.default_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self.last_error = "corrupt_save"
            self._quarantine_corrupt_save()
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
            return True
        except (KeyError, TypeError, ValueError):
            self.last_error = "invalid_schema"
            return False

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

    def _quarantine_corrupt_save(self) -> None:
        try:
            bad_path = self.default_path.with_suffix(".corrupt.json")
            self.default_path.replace(bad_path)
        except OSError:
            # Keep failure silent; load() caller already gets False.
            pass
