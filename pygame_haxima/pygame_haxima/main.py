from __future__ import annotations

from pathlib import Path

import pygame

from pygame_haxima.config import DISPLAY
from pygame_haxima.data.asset_loader import AssetLoader
from pygame_haxima.data.content_registry import ContentRegistry
from pygame_haxima.data.runtime_sprite_probe import converted_runtime_sprite_keys
from pygame_haxima.data.save_manager import SaveManager
from pygame_haxima.data.sprite_profile import load_sprite_profile
from pygame_haxima.data.sprite_atlas import SpriteAtlas
from pygame_haxima.domain.models import GameSession
from pygame_haxima.engine.audio import AudioManager
from pygame_haxima.engine.events import ANIMATION_EVENT
from pygame_haxima.engine.hud import HudPane
from pygame_haxima.engine.input import InputController
from pygame_haxima.engine.keymap import KeyMap
from pygame_haxima.engine.loop import TurnLoop
from pygame_haxima.engine.map_view import MapView
from pygame_haxima.engine.renderer import Renderer
from pygame_haxima.engine.item_sprites import item_sprite_key
from pygame_haxima.engine.text_ui import TextUi


def run() -> int:
    pygame.init()
    pygame.display.set_caption("Pygame Haxima")
    pygame.time.set_timer(ANIMATION_EVENT, 50)
    clock = pygame.time.Clock()

    project_root = Path(__file__).resolve().parents[1]
    assets = AssetLoader(project_root=project_root)
    atlas = SpriteAtlas(assets, project_root=project_root)
    atlas.load()
    report_text = atlas.format_coverage_report()

    renderer = Renderer(
        map_view=MapView(atlas),
        hud=HudPane(),
        text_ui=TextUi(atlas),
    )
    keymap = KeyMap()
    input_controller = InputController(keymap=keymap, renderer=renderer)
    save_manager = SaveManager(project_root / "saves")
    loop = TurnLoop(renderer=renderer, audio=AudioManager(assets), save_manager=save_manager)
    session = ContentRegistry().make_new_session()
    sprite_profile = load_sprite_profile(project_root / "converted_data")
    runtime_sprite_keys = _runtime_sprite_keys(session)
    runtime_sprite_keys.update(converted_runtime_sprite_keys(project_root / "converted_data", sprite_profile))
    runtime_report_text = atlas.format_runtime_coverage_report(runtime_sprite_keys)
    print(report_text, end="")
    print(runtime_report_text, end="")
    coverage_path = project_root / "reports" / "sprite_coverage_report.txt"
    atlas.write_coverage_report(coverage_path)
    with coverage_path.open("a", encoding="utf-8") as handle:
        handle.write("\n")
        handle.write(runtime_report_text)
    terrain_sprite_keys = {
        terrain.sprite_key for terrain in session.place.terrain_defs.values() if terrain.sprite_key
    }
    session.terrain_fallback_keys = sorted(key for key in terrain_sprite_keys if atlas.is_fallback(key))
    session.terrain_fallback_key_count = len(session.terrain_fallback_keys)
    session.option_scale = renderer.scale
    session.option_fullscreen = renderer.is_fullscreen
    session.save_slot_labels = save_manager.list_slots()
    session.command_prompt = "Command> (H help, F10 options)"
    keybind_order = [
        ("move_n", "Move north"),
        ("move_s", "Move south"),
        ("move_w", "Move west"),
        ("move_e", "Move east"),
        ("talk", "Talk"),
        ("open", "Open"),
        ("get", "Get"),
        ("attack", "Attack"),
        ("cast", "Cast spell"),
        ("cycle_spell", "Cycle spell"),
        ("spellbook_menu", "Spellbook"),
        ("reagents_menu", "Reagents list"),
        ("options_menu", "Options menu"),
        ("debug_runtime_state", "Runtime state debug"),
    ]
    session.keybind_preview = [
        f"{label}: {', '.join(pygame.key.name(key) for key in keymap.bindings[action])}"
        for action, label in keybind_order
    ]

    while session.running:
        events = input_controller.poll(session)
        loop.process_events(session, events)
        renderer.render(session)
        clock.tick(DISPLAY.target_fps)

    pygame.quit()
    return 0


def _runtime_sprite_keys(session: GameSession) -> set[str]:
    keys: set[str] = set()
    if session.party.members:
        keys.add(session.party.lead().sprite_key)
    for npc in session.place.npcs:
        keys.add(npc.sprite_key)
    for monster in session.place.monsters:
        keys.add(monster.sprite_key)
    for chest in session.place.chests:
        keys.add(chest.sprite_key)
    for items in session.place.ground_items.values():
        for item in items:
            keys.add(item_sprite_key(item))
    for item in session.party.inventory:
        keys.add(item_sprite_key(item))
    return {key for key in keys if key}
