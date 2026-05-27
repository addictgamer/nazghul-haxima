from __future__ import annotations

from pygame_haxima.data.asset_loader import AssetLoader


class AudioManager:
    def __init__(self, asset_loader: AssetLoader) -> None:
        self.asset_loader = asset_loader
        self.enabled = True

    def play_effect(self, rel_path: str) -> None:
        if not self.enabled:
            return
        sound = self.asset_loader.load_sound(rel_path)
        if sound is not None:
            sound.play()
