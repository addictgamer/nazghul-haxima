from __future__ import annotations

import pygame

from pygame_haxima.data.sprite_atlas import SpriteAtlas
from pygame_haxima.domain.models import GameSession
from pygame_haxima.engine.item_sprites import item_sprite_key
from pygame_haxima.engine.spells import get_spell


class TextUi:
    SAVE_LOAD_PANEL = pygame.Rect(220, 180, 840, 480)

    def __init__(self, atlas: SpriteAtlas) -> None:
        self.atlas = atlas
        self.console_font = self._choose_font(["consolas", "dejavusansmono", "menlo"], 20)
        self.cmd_font = self._choose_font(["consolas", "dejavusansmono", "menlo"], 22, bold=True)
        self.menu_font = self._choose_font(["consolas", "dejavusansmono", "menlo"], 20)
        self.small_font = self._choose_font(["consolas", "dejavusansmono", "menlo"], 16)

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
        spell_panel_h = min(inv_panel.height - 60, max(200, int(inv_panel.height * 0.45)))
        spell_panel = pygame.Rect(
            inv_panel.x + 6,
            inv_panel.bottom - spell_panel_h - 6,
            inv_panel.width - 12,
            spell_panel_h,
        )
        inv_list_rect = pygame.Rect(
            inv_panel.x + 6,
            inv_panel.y + 34,
            inv_panel.width - 12,
            max(40, spell_panel.y - (inv_panel.y + 34) - 6),
        )

        inv_title = self.cmd_font.render("Inventory", True, (235, 225, 175))
        surface.blit(inv_title, (inv_panel.x + 8, inv_panel.y + 6))

        icon_size = 24
        row_h = 28
        y = inv_list_rect.y
        visible_rows = max(1, inv_list_rect.height // row_h)
        items = session.party.inventory[-visible_rows:]
        if not items:
            empty = self.menu_font.render("(empty)", True, (145, 155, 175))
            surface.blit(empty, (inv_panel.x + 10, y))
        else:
            for item in items:
                icon = pygame.transform.scale(self.atlas.get(item_sprite_key(item)), (icon_size, icon_size))
                surface.blit(icon, (inv_panel.x + 8, y))
                label = self.menu_font.render(item.name, True, (210, 220, 238))
                surface.blit(label, (inv_panel.x + 38, y + 3))
                y += row_h

        self._draw_spell_panel(surface, spell_panel, session)

        if session.debug_runtime_state:
            self._draw_runtime_debug_panel(surface, rect, session)

    def _draw_spell_panel(self, surface: pygame.Surface, rect: pygame.Rect, session: GameSession) -> None:
        pygame.draw.rect(surface, (24, 26, 38), rect)
        pygame.draw.rect(surface, (120, 140, 190), rect, 1)
        title = self.cmd_font.render("Spellbook", True, (205, 225, 255))
        surface.blit(title, (rect.x + 8, rect.y + 6))

        selected_id = session.party.selected_spell
        selected_spell = get_spell(selected_id)
        selected_name = selected_spell.name if selected_spell is not None else selected_id
        selected_line = self.menu_font.render(f"Selected: {selected_name}", True, (190, 215, 245))
        surface.blit(selected_line, (rect.x + 8, rect.y + 36))

        known = [spell_id for spell_id in session.party.spells_known if get_spell(spell_id) is not None]
        for idx, spell_id in enumerate(known[:3]):
            spell = get_spell(spell_id)
            if spell is None:
                continue
            marker = ">" if spell_id == selected_id else " "
            line = self.menu_font.render(f"{marker} {spell.name}", True, (175, 195, 230))
            surface.blit(line, (rect.x + 8, rect.y + 58 + idx * 18))

        reagent_y = rect.y + 58 + min(3, len(known)) * 18 + 4
        reag_title = self.small_font.render("Reagents:", True, (170, 210, 180))
        surface.blit(reag_title, (rect.x + 8, reagent_y))
        reagent_y += reag_title.get_height() + 2
        reagents = sorted(session.party.reagents.items())
        if not reagents:
            text = self.small_font.render("none", True, (150, 160, 185))
            surface.blit(text, (rect.x + 8, reagent_y))
        else:
            selected_spell = get_spell(selected_id)
            priority = set(selected_spell.reagents.keys()) if selected_spell is not None else set()
            ordered = sorted(
                reagents,
                key=lambda pair: (pair[0] not in priority, pair[0]),
            )
            line_h = self.small_font.get_height() + 1
            max_rows = max(1, (rect.bottom - reagent_y - 4) // line_h)
            for idx, (name, qty) in enumerate(ordered[:max_rows]):
                prefix = "*" if name in priority else "-"
                pretty = self._pretty_reagent_name(name)
                line = self.small_font.render(f"{prefix} {pretty}: {qty}", True, (170, 210, 180))
                surface.blit(line, (rect.x + 8, reagent_y + idx * line_h))
            if len(ordered) > max_rows:
                more = self.small_font.render(f"+{len(ordered) - max_rows} more", True, (140, 155, 180))
                surface.blit(more, (rect.x + 8, rect.bottom - self.small_font.get_height() - 4))

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
        if session.show_reagents_menu:
            self.draw_reagents_menu(surface, session)

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
        panel = self.SAVE_LOAD_PANEL
        pygame.draw.rect(surface, (18, 20, 32), panel)
        pygame.draw.rect(surface, (170, 185, 225), panel, 2)

        mode = (session.save_load_mode or "save").upper()
        title = self.cmd_font.render(f"{mode} SLOTS", True, (245, 235, 180))
        surface.blit(title, (panel.x + 16, panel.y + 12))
        hint = self.menu_font.render(
            "Arrows/mouse: select slot | Enter or Confirm button | Esc/Close button", True, (200, 210, 225)
        )
        surface.blit(hint, (panel.x + 16, panel.y + 46))

        labels = session.save_slot_labels or [f"Slot {i + 1}: (empty)" for i in range(6)]
        for idx, label in enumerate(labels):
            row_rect = self._save_slot_row_rect(idx)
            selected = idx == session.save_load_selected_slot
            bg = (58, 72, 105) if selected else (28, 34, 52)
            border = (230, 235, 255) if selected else (110, 125, 165)
            pygame.draw.rect(surface, bg, row_rect)
            pygame.draw.rect(surface, border, row_rect, 2 if selected else 1)
            color = (250, 250, 255) if selected else (190, 200, 225)
            marker = ">" if selected else " "
            row = self.menu_font.render(f"{marker} {label}", True, color)
            surface.blit(row, (row_rect.x + 10, row_rect.y + 11))

        for button, button_rect in self._save_load_button_rects().items():
            if button == "confirm":
                label = "SAVE NOW" if (session.save_load_mode or "save") == "save" else "LOAD NOW"
                fill = (70, 105, 78)
            elif button == "mode_save":
                label = "SAVE MODE"
                fill = (58, 66, 96)
            elif button == "mode_load":
                label = "LOAD MODE"
                fill = (58, 66, 96)
            else:
                label = "CLOSE"
                fill = (96, 62, 62)
            active = (
                (button == "mode_save" and (session.save_load_mode or "save") == "save")
                or (button == "mode_load" and (session.save_load_mode or "save") == "load")
            )
            if active:
                fill = (86, 106, 160)
            pygame.draw.rect(surface, fill, button_rect)
            pygame.draw.rect(surface, (225, 230, 245), button_rect, 2)
            txt = self.menu_font.render(label, True, (240, 245, 255))
            tx = button_rect.x + (button_rect.width - txt.get_width()) // 2
            ty = button_rect.y + (button_rect.height - txt.get_height()) // 2
            surface.blit(txt, (tx, ty))

    def draw_reagents_menu(self, surface: pygame.Surface, session: GameSession) -> None:
        panel = pygame.Rect(260, 170, 760, 520)
        pygame.draw.rect(surface, (18, 20, 32), panel)
        pygame.draw.rect(surface, (170, 185, 225), panel, 2)

        title = self.cmd_font.render("REAGENT INVENTORY", True, (245, 235, 180))
        surface.blit(title, (panel.x + 16, panel.y + 12))
        hint = self.menu_font.render("Press R or Esc to close", True, (200, 210, 225))
        surface.blit(hint, (panel.x + 16, panel.y + 46))

        reagents = sorted(session.party.reagents.items())
        if not reagents:
            empty = self.menu_font.render("(none)", True, (160, 170, 190))
            surface.blit(empty, (panel.x + 20, panel.y + 88))
            return

        row_h = 28
        y = panel.y + 86
        max_rows = max(1, (panel.height - 106) // row_h)
        for name, qty in reagents[:max_rows]:
            color = (170, 210, 180) if qty > 0 else (255, 110, 110)
            row = self.menu_font.render(f"{self._pretty_reagent_name(name)}: {qty}", True, color)
            surface.blit(row, (panel.x + 20, y))
            y += row_h

    def save_load_hit_test(self, ui_pos: tuple[int, int], session: GameSession) -> tuple[str, int | None] | None:
        panel = self.SAVE_LOAD_PANEL
        if not panel.collidepoint(ui_pos):
            return None
        for idx in range(len(session.save_slot_labels or [])):
            if self._save_slot_row_rect(idx).collidepoint(ui_pos):
                return ("slot", idx)
        for key, rect in self._save_load_button_rects().items():
            if rect.collidepoint(ui_pos):
                return (key, None)
        return None

    def _save_slot_row_rect(self, idx: int) -> pygame.Rect:
        panel = self.SAVE_LOAD_PANEL
        return pygame.Rect(panel.x + 20, panel.y + 86 + idx * 58, panel.width - 40, 46)

    def _save_load_button_rects(self) -> dict[str, pygame.Rect]:
        panel = self.SAVE_LOAD_PANEL
        y = panel.bottom - 56
        return {
            "confirm": pygame.Rect(panel.x + 20, y, 180, 36),
            "mode_save": pygame.Rect(panel.x + 220, y, 160, 36),
            "mode_load": pygame.Rect(panel.x + 396, y, 160, 36),
            "close": pygame.Rect(panel.right - 140, y, 120, 36),
        }

    def _draw_runtime_debug_panel(
        self, surface: pygame.Surface, sidebar_rect: pygame.Rect, session: GameSession
    ) -> None:
        panel = pygame.Rect(sidebar_rect.x + 8, sidebar_rect.y + 8, sidebar_rect.width - 16, 220)
        pygame.draw.rect(surface, (32, 20, 24), panel)
        pygame.draw.rect(surface, (205, 120, 120), panel, 1)
        title = self.menu_font.render("Debug Runtime State (F4)", True, (255, 205, 170))
        surface.blit(title, (panel.x + 8, panel.y + 6))

        lines: list[str] = []
        lines.append(f"Quest flags: {len(session.quest_flags)}")
        for key in sorted(session.quest_flags.keys())[:6]:
            lines.append(f"- {key}={session.quest_flags[key]}")
        lines.append(f"NPC states: {len(session.npc_states)}")
        for npc_id in sorted(session.npc_states.keys())[:4]:
            state = session.npc_states[npc_id]
            talk_count = state.get("talk_count", 0)
            last_turn = state.get("last_turn", "?")
            lines.append(f"- {npc_id}: talks={talk_count}, turn={last_turn}")

        y = panel.y + 34
        for line in lines[:10]:
            rendered = self.menu_font.render(str(line), True, (245, 220, 220))
            surface.blit(rendered, (panel.x + 8, y))
            y += 18

    def _pretty_reagent_name(self, reagent_id: str) -> str:
        normalized = reagent_id.strip().lower()
        special = {
            "sulphorous_ash": "Sulphurous Ash",
            "sulphurous_ash": "Sulphurous Ash",
        }
        if normalized in special:
            return special[normalized]
        return reagent_id.replace("_", " ").title()
