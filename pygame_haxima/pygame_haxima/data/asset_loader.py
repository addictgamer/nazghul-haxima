from __future__ import annotations

from pathlib import Path

import pygame


class AssetLoader:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.world_dir = project_root.parent / "worlds" / "haxima-1.002"
        self.cache: dict[str, pygame.Surface] = {}

    def _resolve(self, rel_path: str) -> Path:
        return self.world_dir / rel_path

    def load_image(self, rel_path: str) -> pygame.Surface | None:
        key = f"img:{rel_path}"
        if key in self.cache:
            return self.cache[key]
        path = self._resolve(rel_path)
        if not path.exists():
            return None
        image = pygame.image.load(str(path))
        # convert/convert_alpha require an initialized display surface.
        if pygame.display.get_surface() is not None:
            if image.get_alpha() is not None:
                image = image.convert_alpha()
            else:
                image = image.convert()
        self.cache[key] = image
        return image

    def load_sound(self, rel_path: str) -> pygame.mixer.Sound | None:
        path = self._resolve(rel_path)
        if not path.exists():
            return None
        try:
            return pygame.mixer.Sound(str(path))
        except pygame.error:
            return None
