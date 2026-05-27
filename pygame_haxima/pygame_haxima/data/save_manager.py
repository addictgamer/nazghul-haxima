from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from pygame_haxima.domain.models import GameSession, Item, Mode


class SaveManager:
    def __init__(self, save_dir: Path) -> None:
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.default_path = self.save_dir / "tutorial-save.json"

    def save(self, session: GameSession) -> Path:
        payload = {
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
            "clock_hours": session.clock_hours,
            "clock_minutes": session.clock_minutes,
            "log_lines": session.log_lines[-30:],
            "chests": [
                {
                    "chest_id": chest.chest_id,
                    "opened": chest.opened,
                    "items": [asdict(item) for item in chest.items],
                }
                for chest in session.place.chests
            ],
            "monsters": [asdict(monster) for monster in session.place.monsters],
        }
        self.default_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.default_path

    def load(self, session: GameSession) -> bool:
        if not self.default_path.exists():
            return False
        payload = json.loads(self.default_path.read_text(encoding="utf-8"))
        session.party.x = payload["party"]["x"]
        session.party.y = payload["party"]["y"]
        session.party.gold = payload["party"]["gold"]
        session.party.food = payload["party"]["food"]
        session.party.turn_count = payload["party"]["turn_count"]
        session.party.inventory = [Item(**item) for item in payload["party"].get("inventory", [])]
        session.mode = Mode(payload["mode"])
        session.clock_hours = payload["clock_hours"]
        session.clock_minutes = payload["clock_minutes"]
        session.log_lines = payload["log_lines"]
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
        return True
