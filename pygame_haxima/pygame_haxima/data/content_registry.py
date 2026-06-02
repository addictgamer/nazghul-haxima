from __future__ import annotations

import os
from pathlib import Path

from pygame_haxima.data.place_loader import build_place_by_key
from pygame_haxima.data.place_placements import place_key_from_id
from pygame_haxima.data.quest_engine import QuestEngine
from pygame_haxima.data.sprite_profile import load_sprite_profile
from pygame_haxima.domain.models import GameSession, Mode
from pygame_haxima.engine.spells import known_spell_ids


class ContentRegistry:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.converted_data_dir = self.project_root / "converted_data"
        self.quest_engine = QuestEngine.load(self.converted_data_dir)

    def default_place_key(self) -> str:
        return os.environ.get("HAXIMA_PLACE", "tutorial").strip().lower() or "tutorial"

    def make_new_session(self, place_key: str | None = None) -> GameSession:
        key = (place_key or self.default_place_key()).strip().lower()
        sprite_profile = load_sprite_profile(self.converted_data_dir)
        place, party = build_place_by_key(key, self.converted_data_dir, sprite_profile)
        party.spells_known = known_spell_ids()
        if "spark" in party.spells_known:
            party.selected_spell = "spark"
        elif party.spells_known:
            party.selected_spell = party.spells_known[0]
        session = GameSession(place=place, party=party)
        session.append_log("Welcome to the Pygame Haxima redesign.")
        session.append_log(f"Loaded place: {place.name} ({place.place_id}).")
        session.append_log("Move with arrows/WASD. Press H for help.")
        self.quest_engine.bootstrap_new_game(session)
        self.quest_engine.on_place_enter(session)
        return session

    def rebuild_place_for_load(self, session: GameSession, saved_place_id: str) -> None:
        if session.place.place_id == saved_place_id:
            return
        key = place_key_from_id(saved_place_id)
        sprite_profile = load_sprite_profile(self.converted_data_dir)
        place, _ = build_place_by_key(key, self.converted_data_dir, sprite_profile)
        session.place = place

    def travel_to(self, session: GameSession, place_key: str) -> None:
        sprite_profile = load_sprite_profile(self.converted_data_dir)
        place, party = build_place_by_key(place_key, self.converted_data_dir, sprite_profile)
        party.spells_known = list(session.party.spells_known)
        party.selected_spell = session.party.selected_spell
        party.reagents = dict(session.party.reagents)
        party.inventory = list(session.party.inventory)
        party.gold = session.party.gold
        party.food = session.party.food
        party.turn_count = session.party.turn_count
        party.ward_charges = session.party.ward_charges
        session.place = place
        session.party = party
        session.targeting_action = None
        session.target_cursor = None
        session.mode = Mode.EXPLORE
        session.combat.active = False
        session.combat.enemy_ids = []
        session.append_log(f"Traveled to {place.name}.")
        self.quest_engine.on_place_enter(session)
