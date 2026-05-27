from __future__ import annotations

from pygame_haxima.data.tutorial_slice import build_tutorial_place
from pygame_haxima.domain.models import GameSession


class ContentRegistry:
    def make_new_session(self) -> GameSession:
        place, party = build_tutorial_place()
        session = GameSession(place=place, party=party)
        session.append_log("Welcome to the Pygame Haxima redesign.")
        session.append_log("Move with arrows/WASD. Press H for help.")
        return session
