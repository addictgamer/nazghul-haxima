from __future__ import annotations

import pygame

from pygame_haxima.config import DISPLAY
from pygame_haxima.data.asset_loader import AssetLoader

# Matches worlds/haxima-1.002/kern-init.scm splash keys and src/nazghul.c lookup.
SPLASH_BY_RESOLUTION: tuple[tuple[tuple[int, int], str], ...] = (
    ((1280, 960), "splash.png"),
    ((800, 480), "640x480_splash.png"),
    ((640, 480), "640x480_splash.png"),
)

TITLE_HUD_HEIGHT = 70
TITLE_SIDEBAR_WIDTH = 320


def splash_filename_for_display(
    width: int = DISPLAY.base_width,
    height: int = DISPLAY.base_height,
) -> str:
    for (res_w, res_h), filename in SPLASH_BY_RESOLUTION:
        if width >= res_w and height >= res_h:
            return filename
    return "640x480_splash.png"


def load_title_splash(asset_loader: AssetLoader) -> pygame.Surface | None:
    for _dims, filename in SPLASH_BY_RESOLUTION:
        surface = asset_loader.load_image(filename)
        if surface is not None:
            return surface
    return asset_loader.load_image(splash_filename_for_display())


def title_art_rect(
    width: int = DISPLAY.base_width,
    height: int = DISPLAY.base_height,
) -> pygame.Rect:
    """Map-view region on the left, as in the original Nazghul main menu."""
    art_w = width - TITLE_SIDEBAR_WIDTH
    art_h = height - TITLE_HUD_HEIGHT
    return pygame.Rect(0, TITLE_HUD_HEIGHT, art_w, art_h)


def blit_splash_in_rect(
    target: pygame.Surface,
    splash: pygame.Surface,
    area: pygame.Rect,
) -> pygame.Rect:
    sw, sh = splash.get_width(), splash.get_height()
    if sw <= 0 or sh <= 0 or area.width <= 0 or area.height <= 0:
        return area
    scale = min(area.width / sw, area.height / sh, 1.0)
    dest_w = max(1, int(sw * scale))
    dest_h = max(1, int(sh * scale))
    if (dest_w, dest_h) != (sw, sh):
        image = pygame.transform.smoothscale(splash, (dest_w, dest_h))
    else:
        image = splash
    dest = pygame.Rect(0, 0, dest_w, dest_h)
    dest.center = area.center
    target.blit(image, dest.topleft)
    return dest


def draw_title_backdrop(surface: pygame.Surface, art_area: pygame.Rect) -> None:
    pygame.draw.rect(surface, (10, 12, 20), art_area)
    pygame.draw.rect(surface, (45, 55, 85), art_area, 1)
