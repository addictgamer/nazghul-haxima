from __future__ import annotations

import pygame

from pygame_haxima.data.sprite_atlas import SpriteAtlas
from pygame_haxima.domain.models import GameSession
from pygame_haxima.engine.item_sprites import item_sprite_key


class TextUi:
    def __init__(self, atlas: SpriteAtlas) -> None:
        self.atlas = atlas
        self.console_font = self._choose_font(["consolas", "dejavusansmono", "menlo"], 20)
        self.cmd_font = self._choose_font(["consolas", "dejavusansmono", "menlo"], 22, bold=True)
        self.menu_font = self._choose_font(["consolas", "dejavusansmono", "menlo"], 20)

    def _choose_font(self, candidates: list[str], size: int, bold: bool = False) -> pygame.font.Font:
        for name in candidates:
            matched = pygame.font.match_font(name, bold=bold)
            if matched:
                return pygame.font.Font(matched, size)
        return pygame.font.SysFont(None, size, bold=bold)

    def _wrap_text(self, font: pygame.font.Font, text: str, max_width: int) -> list[str]:
        if not text:
            return [""]
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def draw_console(self, surface: pygame.Surface, rect: pygame.Rect, session: GameSession) -> None:
        pygame.draw.rect(surface, (12, 12, 16), rect)
        pygame.draw.rect(surface, (80, 80, 95), rect, 1)
        y_cursor = rect.y + 8
        max_width = rect.width - 16

        if session.dialogue_lines:
            y_cursor = self._draw_dialogue_panel(surface, rect, session, y_cursor)

        wrapped_logs: list[str] = []
        for line in session.log_lines[-28:]:
            wrapped_logs.extend(self._wrap_text(self.console_font, line, max_width))
        line_height = 20
        available_height = max(0, (rect.bottom - 8) - y_cursor)
        max_visible_lines = max(1, available_height // line_height)
        visible_lines = wrapped_logs[-max_visible_lines:]
        for index, line in enumerate(visible_lines):
            rendered = self.console_font.render(line, True, (190, 210, 190))
            surface.blit(rendered, (rect.x + 8, y_cursor + index * line_height))

    def _draw_dialogue_panel(
        self, surface: pygame.Surface, rect: pygame.Rect, session: GameSession, y_cursor: int
    ) -> int:
        panel_h = 78
        panel = pygame.Rect(rect.x + 6, y_cursor, rect.width - 12, panel_h)
        pygame.draw.rect(surface, (28, 30, 44), panel)
        pygame.draw.rect(surface, (130, 140, 180), panel, 1)
        speaker = session.dialogue_speaker or "Unknown"
        title = self.menu_font.render(f"{speaker} says:", True, (250, 220, 150))
        surface.blit(title, (panel.x + 8, panel.y + 4))
        max_width = panel.width - 16
        dialogue_text = " ".join(session.dialogue_lines)
        wrapped = self._wrap_text(self.console_font, dialogue_text, max_width)
        for index, line in enumerate(wrapped[:2]):
            rendered = self.console_font.render(line, True, (220, 225, 245))
            surface.blit(rendered, (panel.x + 8, panel.y + 28 + index * 20))
        return y_cursor + panel_h + 6

    def draw_sidebar(self, surface: pygame.Surface, rect: pygame.Rect, session: GameSession) -> None:
        pygame.draw.rect(surface, (14, 14, 20), rect)
        pygame.draw.rect(surface, (85, 95, 120), rect, 1)
        lead = session.party.lead()

        panel_pad = 8
        char_panel_h = 230
        char_panel = pygame.Rect(
            rect.x + panel_pad, rect.y + panel_pad, rect.width - panel_pad * 2, char_panel_h
        )
        pygame.draw.rect(surface, (22, 24, 32), char_panel)
        pygame.draw.rect(surface, (115, 130, 170), char_panel, 1)
        title = self.cmd_font.render("Character", True, (245, 225, 160))
        surface.blit(title, (char_panel.x + 8, char_panel.y + 8))
        portrait = pygame.transform.scale(self.atlas.get(lead.sprite_key), (48, 48))
        surface.blit(portrait, (char_panel.x + 8, char_panel.y + 42))
        name = self.menu_font.render(lead.name, True, (220, 230, 245))
        surface.blit(name, (char_panel.x + 64, char_panel.y + 46))
        rows = [
            f"HP: {lead.hp}/{lead.max_hp}",
            f"AP: {lead.ap}",
            f"ATK: {lead.attack}  DEF: {lead.defense}",
            f"Food: {session.party.food}  Gold: {session.party.gold}",
            f"Turn: {session.party.turn_count}",
            f"Time: {session.clock_hours:02d}:{session.clock_minutes:02d}",
        ]
        for idx, row in enumerate(rows):
            text = self.menu_font.render(row, True, (190, 205, 225))
            surface.blit(text, (char_panel.x + 8, char_panel.y + 96 + idx * 20))

        inv_panel = pygame.Rect(
            rect.x + panel_pad,
            char_panel.bottom + panel_pad,
            rect.width - panel_pad * 2,
            rect.bottom - (char_panel.bottom + panel_pad) - panel_pad,
        )
        pygame.draw.rect(surface, (20, 22, 30), inv_panel)
        pygame.draw.rect(surface, (105, 120, 155), inv_panel, 1)
        inv_title = self.cmd_font.render("Inventory", True, (235, 225, 175))
        surface.blit(inv_title, (inv_panel.x + 8, inv_panel.y + 8))

        icon_size = 24
        row_h = 30
        y = inv_panel.y + 42
        visible_rows = max(1, (inv_panel.height - 50) // row_h)
        items = session.party.inventory[-visible_rows:]
        if not items:
            empty = self.menu_font.render("(empty)", True, (145, 155, 175))
            surface.blit(empty, (inv_panel.x + 10, y))
            return
        for item in items:
            icon = pygame.transform.scale(self.atlas.get(item_sprite_key(item)), (icon_size, icon_size))
            surface.blit(icon, (inv_panel.x + 8, y))
            label = self.menu_font.render(item.name, True, (210, 220, 238))
            surface.blit(label, (inv_panel.x + 38, y + 3))
            y += row_h

    def draw_command(self, surface: pygame.Surface, rect: pygame.Rect, session: GameSession) -> None:
        pygame.draw.rect(surface, (16, 16, 22), rect)
        pygame.draw.rect(surface, (110, 110, 140), rect, 1)
        prompt = self.cmd_font.render(session.command_prompt, True, (230, 220, 120))
        surface.blit(prompt, (rect.x + 8, rect.y + 6))
        if session.show_save_load_menu:
            self.draw_save_load_menu(surface, session)
            return
        if session.show_options_menu:
            self.draw_options_menu(surface, session)

    def draw_options_menu(self, surface: pygame.Surface, session: GameSession) -> None:
        panel = pygame.Rect(170, 170, 940, 520)
        pygame.draw.rect(surface, (20, 22, 34), panel)
        pygame.draw.rect(surface, (160, 170, 210), panel, 2)

        title = self.cmd_font.render("Options", True, (245, 235, 180))
        surface.blit(title, (panel.x + 16, panel.y + 12))

        options = [
            f"Scale: {session.option_scale}x",
            f"Fullscreen: {'On' if session.option_fullscreen else 'Off'}",
            f"Terrain IDs (F2): {'On' if session.debug_terrain_ids else 'Off'}",
            f"Sprite warnings (F3): {'On' if session.debug_sprite_warnings else 'Off'}",
        ]
        for index, text in enumerate(options):
            color = (240, 240, 255) if index == session.options_selected_index else (170, 180, 200)
            prefix = ">" if index == session.options_selected_index else " "
            line = self.menu_font.render(f"{prefix} {text}", True, color)
            surface.blit(line, (panel.x + 20, panel.y + 60 + index * 28))

        hint = self.menu_font.render("Use arrows: up/down select, left/right change, Esc/F10 close", True, (215, 205, 140))
        surface.blit(hint, (panel.x + 20, panel.y + 190))

        preview_title = self.menu_font.render("Keybind preview:", True, (200, 220, 240))
        surface.blit(preview_title, (panel.x + 20, panel.y + 235))
        for index, line in enumerate(session.keybind_preview[:9]):
            row = self.menu_font.render(f"- {line}", True, (175, 195, 220))
            surface.blit(row, (panel.x + 28, panel.y + 265 + index * 24))

    def draw_save_load_menu(self, surface: pygame.Surface, session: GameSession) -> None:
        panel = pygame.Rect(220, 180, 840, 480)
        pygame.draw.rect(surface, (18, 20, 32), panel)
        pygame.draw.rect(surface, (170, 185, 225), panel, 2)

        mode = (session.save_load_mode or "save").upper()
        title = self.cmd_font.render(f"{mode} SLOTS", True, (245, 235, 180))
        surface.blit(title, (panel.x + 16, panel.y + 12))
        hint = self.menu_font.render("Arrows: select slot | Enter: confirm | Esc: close", True, (200, 210, 225))
        surface.blit(hint, (panel.x + 16, panel.y + 46))

        labels = session.save_slot_labels or [f"Slot {i + 1}: (empty)" for i in range(6)]
        for idx, label in enumerate(labels):
            selected = idx == session.save_load_selected_slot
            color = (245, 245, 255) if selected else (180, 190, 215)
            marker = ">" if selected else " "
            row = self.menu_font.render(f"{marker} {label}", True, color)
            surface.blit(row, (panel.x + 24, panel.y + 88 + idx * 52))
