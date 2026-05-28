from __future__ import annotations

from pathlib import Path

from pygame_haxima.data.sprite_profile import load_sprite_profile
from pygame_haxima.data.tutorial_slice import build_tutorial_place
from pygame_haxima.domain.models import GameSession


class ContentRegistry:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]

    def make_new_session(self) -> GameSession:
        sprite_profile = load_sprite_profile(self.project_root / "converted_data")
        place, party = build_tutorial_place(sprite_profile)
        session = GameSession(place=place, party=party)
        session.append_log("Welcome to the Pygame Haxima redesign.")
        session.append_log("Move with arrows/WASD. Press H for help.")
        return session
