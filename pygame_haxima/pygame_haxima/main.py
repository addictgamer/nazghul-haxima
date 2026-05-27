from __future__ import annotations

from pathlib import Path

import pygame

from pygame_haxima.config import DISPLAY
from pygame_haxima.data.asset_loader import AssetLoader
from pygame_haxima.data.content_registry import ContentRegistry
from pygame_haxima.data.save_manager import SaveManager
from pygame_haxima.data.sprite_atlas import SpriteAtlas
from pygame_haxima.engine.audio import AudioManager
from pygame_haxima.engine.events import ANIMATION_EVENT
from pygame_haxima.engine.hud import HudPane
from pygame_haxima.engine.input import InputController
from pygame_haxima.engine.keymap import KeyMap
from pygame_haxima.engine.loop import TurnLoop
from pygame_haxima.engine.map_view import MapView
from pygame_haxima.engine.renderer import Renderer
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

    renderer = Renderer(
        map_view=MapView(atlas),
        hud=HudPane(),
        text_ui=TextUi(),
    )
    input_controller = InputController(keymap=KeyMap(), renderer=renderer)
    save_manager = SaveManager(project_root / "saves")
    loop = TurnLoop(renderer=renderer, audio=AudioManager(assets), save_manager=save_manager)
    session = ContentRegistry().make_new_session()

    while session.running:
        events = input_controller.poll(session)
        loop.process_events(session, events)
        renderer.render(session)
        clock.tick(DISPLAY.target_fps)

    pygame.quit()
    return 0
