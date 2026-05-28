from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayConfig:
    base_width: int = 1280
    base_height: int = 960
    tile_w: int = 32
    tile_h: int = 32
    scale: int = 1
    fullscreen: bool = False
    target_fps: int = 60


@dataclass(frozen=True)
class LayoutConfig:
    map_tiles_w: int = 23
    map_tiles_h: int = 18
    console_lines: int = 9


DISPLAY = DisplayConfig()
LAYOUT = LayoutConfig()
