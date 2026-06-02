from pathlib import Path

from pygame_haxima.data.content_registry import ContentRegistry
from pygame_haxima.data.quest_engine import QuestEngine
from pygame_haxima.data.tutorial_slice import build_tutorial_place
from pygame_haxima.domain.models import GameSession


def test_quest_engine_bootstraps_whereami() -> None:
    root = Path(__file__).resolve().parents[1]
    engine = QuestEngine.load(root / "converted_data")
    place, party = build_tutorial_place()
    session = GameSession(place=place, party=party)
    engine.bootstrap_new_game(session)
    active = session.quest_progress.get("active")
    assert isinstance(active, dict)
    assert "questentry-whereami" in active


def test_cloviskeep_entry_assigns_call_to_arms() -> None:
    root = Path(__file__).resolve().parents[1]
    registry = ContentRegistry(root)
    session = registry.make_new_session("cloviskeep")
    active = session.quest_progress.get("active")
    assert isinstance(active, dict)
    assert "questentry-calltoarms" in active


def test_talk_to_guard_completes_whereami() -> None:
    root = Path(__file__).resolve().parents[1]
    registry = ContentRegistry(root)
    session = registry.make_new_session("cloviskeep")
    registry.quest_engine.on_talk(session, "clovis_guard")
    active = session.quest_progress.get("active")
    assert isinstance(active, dict)
    assert active.get("questentry-whereami", {}).get("stage") == "completed"
