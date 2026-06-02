from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pygame_haxima.domain.models import GameSession


@dataclass(frozen=True)
class QuestRecord:
    quest_id: str
    title: str
    description: str


class QuestEngine:
    def __init__(self, records: dict[str, QuestRecord]) -> None:
        self.records = records

    @classmethod
    def load(cls, converted_data_dir: Path) -> QuestEngine:
        records: dict[str, QuestRecord] = {}
        quests_dir = converted_data_dir / "quests"
        if not quests_dir.exists():
            return cls(records)
        for quest_file in quests_dir.glob("*.quests.json"):
            payload = json.loads(quest_file.read_text(encoding="utf-8"))
            for entry in payload.get("quests", []):
                if not isinstance(entry, dict):
                    continue
                quest_id = entry.get("id")
                title = entry.get("title")
                if not isinstance(quest_id, str) or not isinstance(title, str):
                    continue
                preview = entry.get("description_preview", "")
                description = preview if isinstance(preview, str) else ""
                records[quest_id] = QuestRecord(
                    quest_id=quest_id,
                    title=title,
                    description=description,
                )
        return cls(records)

    def bootstrap_new_game(self, session: GameSession) -> None:
        if session.quest_progress.get("bootstrapped"):
            return
        active = session.quest_progress.setdefault("active", {})
        if not isinstance(active, dict):
            session.quest_progress["active"] = {}
            active = session.quest_progress["active"]
        if "questentry-whereami" in self.records:
            active["questentry-whereami"] = {"stage": "assigned"}
        session.quest_progress["bootstrapped"] = True
        session.quest_progress.setdefault("completed", [])

    def on_place_enter(self, session: GameSession) -> None:
        hooks = getattr(session.place, "on_entry_hooks", [])
        if not isinstance(hooks, list):
            return
        for hook in hooks:
            if hook == "on-entry-to-dungeon-room":
                self._assign(session, "questentry-calltoarms")
                session.append_log("Quest updated: urgent word from the Enchanter.")

    def on_talk(self, session: GameSession, npc_id: str) -> None:
        if npc_id in {"mentor", "clovis_guard"}:
            self._complete(session, "questentry-whereami")
            session.append_log("Quest complete: Where am I?")
        if npc_id == "clovis_guard":
            self._set_flag(session, "questentry-calltoarms", "spoke_guard", True)

    def on_chest_opened(self, session: GameSession, chest_id: str) -> None:
        self._set_flag(session, "questentry-thiefrune", f"opened:{chest_id}", True)

    def on_quest_flag(self, session: GameSession, flag_key: str) -> None:
        if flag_key == "quest:ship_raiseable":
            self._assign(session, "questentry-rune-c")
            session.append_log("Quest hint: the sunken ship may now be raised.")

    def active_quest_lines(self, session: GameSession, limit: int = 3) -> list[str]:
        active = session.quest_progress.get("active")
        if not isinstance(active, dict):
            return []
        lines: list[str] = []
        for quest_id, state in active.items():
            record = self.records.get(quest_id)
            title = record.title if record else quest_id
            if isinstance(state, dict) and state.get("stage") == "completed":
                continue
            lines.append(title)
            if len(lines) >= limit:
                break
        return lines

    def _assign(self, session: GameSession, quest_id: str) -> None:
        if quest_id not in self.records:
            return
        active = session.quest_progress.setdefault("active", {})
        if not isinstance(active, dict):
            return
        if quest_id in active and isinstance(active[quest_id], dict):
            current = active[quest_id]
            if current.get("stage") == "completed":
                return
        active[quest_id] = {"stage": "assigned"}
        record = self.records[quest_id]
        session.append_log(f"New quest: {record.title}")

    def _complete(self, session: GameSession, quest_id: str) -> None:
        active = session.quest_progress.get("active")
        if not isinstance(active, dict) or quest_id not in active:
            return
        active[quest_id] = {"stage": "completed"}
        completed = session.quest_progress.setdefault("completed", [])
        if isinstance(completed, list) and quest_id not in completed:
            completed.append(quest_id)

    def _set_flag(self, session: GameSession, quest_id: str, flag: str, value: object) -> None:
        active = session.quest_progress.setdefault("active", {})
        if not isinstance(active, dict):
            return
        state = active.setdefault(quest_id, {"stage": "assigned"})
        if not isinstance(state, dict):
            return
        flags = state.setdefault("flags", {})
        if isinstance(flags, dict):
            flags[flag] = value
