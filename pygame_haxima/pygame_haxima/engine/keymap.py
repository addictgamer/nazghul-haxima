from __future__ import annotations

import pygame


class KeyMap:
    def __init__(self) -> None:
        self.bindings: dict[str, list[int]] = {
            "move_n": [pygame.K_UP, pygame.K_w],
            "move_s": [pygame.K_DOWN, pygame.K_s],
            "move_w": [pygame.K_LEFT, pygame.K_a],
            "move_e": [pygame.K_RIGHT, pygame.K_d],
            "talk": [pygame.K_t],
            "open": [pygame.K_o],
            "get": [pygame.K_g],
            "attack": [pygame.K_f],
            "examine": [pygame.K_x],
            "save": [pygame.K_F5],
            "load": [pygame.K_F9],
            "help": [pygame.K_h],
            "cancel": [pygame.K_ESCAPE],
            "confirm": [pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE],
            "fullscreen": [pygame.K_F11],
            "options_menu": [pygame.K_F10],
            "debug_terrain": [pygame.K_F2],
            "debug_sprite_warnings": [pygame.K_F3],
            "debug_runtime_state": [pygame.K_F4],
        }

    def action_for_key(self, key: int) -> str | None:
        for action, keys in self.bindings.items():
            if key in keys:
                return action
        return None

    def rebind(self, action: str, new_key: int) -> None:
        if action not in self.bindings:
            self.bindings[action] = [new_key]
            return
        self.bindings[action] = [new_key]
