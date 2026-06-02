from __future__ import annotations

import pygame

from pygame_haxima.data.sprite_atlas import SpriteAtlas
from pygame_haxima.domain.models import GameSession, Item
from pygame_haxima.engine.item_sprites import item_sprite_key
from pygame_haxima.engine.main_menu import draw_main_menu
from pygame_haxima.engine.spells import get_spell, spell_context_available


class TextUi:
    SAVE_LOAD_PANEL = pygame.Rect(220, 180, 840, 480)
    SPELLBOOK_PANEL = pygame.Rect(120, 100, 1040, 660)
    SPELLBOOK_TABS: tuple[tuple[str, str], ...] = (
        ("all", "All Spells"),
        ("any", "Anywhere"),
        ("town", "Town"),
        ("world", "World"),
        ("missing", "Missing Reagents"),
    )

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
                icon = pygame.transform.scale(
                    self.atlas.get(item_sprite_key(item, self.atlas.has_key)),
                    (icon_size, icon_size),
                )
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
        selected_icon_size = 14
        selected_text_x = rect.x + 8 + selected_icon_size + 4
        selected_wrapped = self._wrap_text(
            self.small_font, f"Selected: {selected_name}", rect.width - (selected_text_x - rect.x) - 8
        )
        selected_y = rect.y + 36
        if selected_spell is not None:
            selected_icon = pygame.transform.scale(
                self.atlas.get(self._spell_sprite_key(selected_spell)),
                (selected_icon_size, selected_icon_size),
            )
            surface.blit(selected_icon, (rect.x + 8, selected_y + 1))
        for line_text in selected_wrapped[:2]:
            line = self.small_font.render(line_text, True, (190, 215, 245))
            surface.blit(line, (selected_text_x, selected_y))
            selected_y += self.small_font.get_height() + 1

        known = [spell_id for spell_id in session.party.spells_known if get_spell(spell_id) is not None]
        visible_spell_ids: list[str] = []
        if known:
            start_idx = known.index(selected_id) if selected_id in known else 0
            visible_count = min(3, max(0, len(known) - 1))
            visible_spell_ids = [
                known[(start_idx + 1 + offset) % len(known)] for offset in range(visible_count)
            ]
        spell_y = selected_y + 2
        max_spell_rows = 6
        used_rows = 0
        spell_icon_size = 14
        list_indent_x = rect.x + 28
        list_text_x = list_indent_x + spell_icon_size + 4
        for spell_id in visible_spell_ids:
            if used_rows >= max_spell_rows:
                break
            spell = get_spell(spell_id)
            if spell is None:
                continue
            wrapped = self._wrap_text(
                self.small_font,
                spell.name,
                rect.width - (list_text_x - rect.x) - 8,
            )
            context_ok = spell_context_available(spell.context, getattr(session.place, "spell_context", "context-town"))
            reagent_ok = all(
                session.party.reagents.get(reagent, 0) >= qty for reagent, qty in spell.reagents.items()
            )
            if not context_ok:
                color = (230, 185, 145)
            elif not reagent_ok:
                color = (215, 150, 150)
            else:
                color = (175, 195, 230)
            spell_icon = pygame.transform.scale(
                self.atlas.get(self._spell_sprite_key(spell)),
                (spell_icon_size, spell_icon_size),
            )
            drew_icon = False
            for line_text in wrapped[:2]:
                if used_rows >= max_spell_rows:
                    break
                if not drew_icon:
                    surface.blit(spell_icon, (list_indent_x, spell_y + 1))
                    drew_icon = True
                line = self.small_font.render(line_text, True, color)
                surface.blit(line, (list_text_x, spell_y))
                spell_y += self.small_font.get_height() + 1
                used_rows += 1

        reagent_y = spell_y + self.small_font.get_height() + 1
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
            icon_size = 14
            line_h = max(icon_size, self.small_font.get_height()) + 2
            max_rows = max(1, (rect.bottom - reagent_y - 4) // line_h)
            for idx, (name, qty) in enumerate(ordered[:max_rows]):
                prefix = "*" if name in priority else "-"
                pretty = self._pretty_reagent_name(name)
                line = self.small_font.render(f"{prefix} {pretty}: {qty}", True, (170, 210, 180))
                row_y = reagent_y + idx * line_h
                icon = pygame.transform.scale(
                    self.atlas.get(self._reagent_sprite_key(name)),
                    (icon_size, icon_size),
                )
                surface.blit(icon, (rect.x + 8, row_y))
                surface.blit(line, (rect.x + 8 + icon_size + 4, row_y))
            if len(ordered) > max_rows:
                more = self.small_font.render(f"+{len(ordered) - max_rows} more", True, (140, 155, 180))
                surface.blit(more, (rect.x + 8, rect.bottom - self.small_font.get_height() - 4))

    def draw_main_menu_screen(self, surface: pygame.Surface, session: GameSession) -> None:
        draw_main_menu(
            surface,
            selected_index=session.main_menu_selected_index,
            title_font=self.cmd_font,
            menu_font=self.menu_font,
            small_font=self.small_font,
        )
        if session.show_save_load_menu:
            self.draw_save_load_menu(surface, session)
        elif session.show_options_menu:
            self.draw_options_menu(surface, session)

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
        if session.show_spellbook_menu:
            self.draw_spellbook_menu(surface, session)

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
        if not session.show_main_menu:
            options.append("Return to Main Menu")
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

        icon_size = 22
        row_h = 28
        y = panel.y + 86
        max_rows = max(1, (panel.height - 106) // row_h)
        for name, qty in reagents[:max_rows]:
            color = (170, 210, 180) if qty > 0 else (255, 110, 110)
            row = self.menu_font.render(f"{self._pretty_reagent_name(name)}: {qty}", True, color)
            icon = pygame.transform.scale(
                self.atlas.get(self._reagent_sprite_key(name)),
                (icon_size, icon_size),
            )
            surface.blit(icon, (panel.x + 20, y + 1))
            surface.blit(row, (panel.x + 20 + icon_size + 8, y))
            y += row_h

    def draw_spellbook_menu(self, surface: pygame.Surface, session: GameSession) -> None:
        panel = self.SPELLBOOK_PANEL
        pygame.draw.rect(surface, (18, 20, 32), panel)
        pygame.draw.rect(surface, (170, 185, 225), panel, 2)

        title = self.cmd_font.render("SPELLBOOK", True, (245, 235, 180))
        surface.blit(title, (panel.x + 16, panel.y + 12))
        hint = self.menu_font.render(
            "Wheel/Up/Down scroll | Enter set active | C cast | B/Esc close",
            True,
            (200, 210, 225),
        )
        surface.blit(hint, (panel.x + 16, panel.y + 46))
        self._draw_spellbook_tabs(surface, session)

        entries, available_count = self._known_spells(session)
        list_rect = self._spellbook_list_rect()
        detail_rect = self._spellbook_detail_rect()
        pygame.draw.rect(surface, (24, 28, 40), list_rect)
        pygame.draw.rect(surface, (110, 125, 165), list_rect, 1)
        pygame.draw.rect(surface, (24, 28, 40), detail_rect)
        pygame.draw.rect(surface, (110, 125, 165), detail_rect, 1)

        if not entries:
            empty = self.menu_font.render("(No known spells)", True, (180, 190, 210))
            surface.blit(empty, (list_rect.x + 10, list_rect.y + 12))
            for button, button_rect in self._spellbook_button_rects().items():
                label = {"cast": "Cast (C)", "set": "Set Active (Enter)", "close": "Close (B/Esc)"}[button]
                fill = (58, 66, 96) if button != "close" else (96, 62, 62)
                pygame.draw.rect(surface, fill, button_rect)
                pygame.draw.rect(surface, (225, 230, 245), button_rect, 2)
                txt = self.small_font.render(label, True, (240, 245, 255))
                tx = button_rect.x + (button_rect.width - txt.get_width()) // 2
                ty = button_rect.y + (button_rect.height - txt.get_height()) // 2
                surface.blit(txt, (tx, ty))
            return

        selected_idx = max(0, min(session.spellbook_selected_index, len(entries) - 1))
        row_h = 24
        header_h = 24
        visible_rows = max(1, (list_rect.height - header_h - 4) // row_h)
        start_idx = self._spellbook_start_index(len(entries), selected_idx, visible_rows)
        visible = entries[start_idx : start_idx + visible_rows]
        label_ready = self.small_font.render("Ready To Cast", True, (170, 230, 170))
        blocked_left = self.small_font.render("Blocked (reagents/", True, (245, 165, 150))
        blocked_context = self.small_font.render("context", True, (235, 195, 145))
        blocked_right = self.small_font.render(")", True, (245, 165, 150))
        blocked_total_w = (
            blocked_left.get_width() + blocked_context.get_width() + blocked_right.get_width()
        )
        surface.blit(label_ready, (list_rect.x + 8, list_rect.y + 6))
        if available_count < len(entries):
            blocked_x = max(list_rect.x + 170, list_rect.right - blocked_total_w - 8)
            blocked_y = list_rect.y + 6
            surface.blit(blocked_left, (blocked_x, blocked_y))
            blocked_x += blocked_left.get_width()
            surface.blit(blocked_context, (blocked_x, blocked_y))
            blocked_x += blocked_context.get_width()
            surface.blit(blocked_right, (blocked_x, blocked_y))
        for offset, entry in enumerate(visible):
            spell = entry["spell"]
            idx = start_idx + offset
            row_rect = pygame.Rect(
                list_rect.x + 4, list_rect.y + header_h + offset * row_h + 2, list_rect.width - 8, row_h - 2
            )
            hovered = session.spellbook_hover_index == idx
            selected = idx == selected_idx
            active = spell.spell_id == session.party.selected_spell
            if entry["status"] == "ready":
                bg = (70, 88, 128) if hovered else (56, 72, 108) if selected else (30, 38, 60)
            elif entry["status"] == "context":
                bg = (128, 90, 52) if hovered else (106, 74, 44) if selected else (66, 46, 28)
            else:
                bg = (120, 64, 64) if hovered else (98, 52, 52) if selected else (62, 34, 34)
            pygame.draw.rect(surface, bg, row_rect)
            if active:
                pygame.draw.rect(surface, (210, 220, 255), row_rect, 2)
            marker = ">" if selected else " "
            active_marker = "*" if active else " "
            row_icon_size = 16
            row_icon = pygame.transform.scale(
                self.atlas.get(self._spell_sprite_key(spell)),
                (row_icon_size, row_icon_size),
            )
            icon_x = row_rect.x + 6
            icon_y = row_rect.y + (row_rect.height - row_icon_size) // 2
            surface.blit(row_icon, (icon_x, icon_y))
            text = self.small_font.render(
                f"{marker}{active_marker} C{spell.circle} {spell.name}",
                True,
                (255, 235, 210)
                if entry["status"] == "context" and (selected or hovered)
                else (235, 195, 145)
                if entry["status"] == "context"
                else (255, 230, 230)
                if entry["status"] != "ready" and (selected or hovered)
                else (230, 170, 170)
                if entry["status"] != "ready"
                else (240, 245, 255)
                if selected or hovered
                else (180, 195, 220),
            )
            surface.blit(text, (icon_x + row_icon_size + 6, row_rect.y + 5))
            if idx == available_count - 1 and available_count < len(entries):
                divider_y = row_rect.bottom + 1
                pygame.draw.line(
                    surface, (180, 120, 120), (list_rect.x + 6, divider_y), (list_rect.right - 6, divider_y), 2
                )

        focus_idx = session.spellbook_hover_index
        if focus_idx is None or focus_idx < 0 or focus_idx >= len(entries):
            focus_idx = selected_idx
        focus_spell = entries[focus_idx]["spell"]
        self._draw_spellbook_details(surface, detail_rect, session, focus_spell)
        can_cast = self._can_cast_spell(session, focus_spell)
        for button, button_rect in self._spellbook_button_rects().items():
            label = {"cast": "Cast (C)", "set": "Set Active (Enter)", "close": "Close (B/Esc)"}[button]
            if button == "cast":
                fill = (70, 105, 78) if can_cast else (70, 70, 70)
            elif button == "close":
                fill = (96, 62, 62)
            else:
                fill = (58, 66, 96)
            pygame.draw.rect(surface, fill, button_rect)
            pygame.draw.rect(surface, (225, 230, 245), button_rect, 2)
            txt = self.small_font.render(label, True, (240, 245, 255))
            tx = button_rect.x + (button_rect.width - txt.get_width()) // 2
            ty = button_rect.y + (button_rect.height - txt.get_height()) // 2
            surface.blit(txt, (tx, ty))

    def _draw_spellbook_details(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        session: GameSession,
        spell,
    ) -> None:
        icon_size = 28
        y = rect.y + 10
        spell_icon = pygame.transform.scale(
            self.atlas.get(self._spell_sprite_key(spell)),
            (icon_size, icon_size),
        )
        surface.blit(spell_icon, (rect.x + 10, y + 2))
        title = self.cmd_font.render(spell.name, True, (220, 235, 255))
        surface.blit(title, (rect.x + 10 + icon_size + 8, y))
        y += max(title.get_height(), icon_size) + 4
        desc_width = rect.width - 20
        for line in self._wrap_text(self.small_font, self._spell_summary_text(spell), desc_width):
            summary = self.small_font.render(line, True, (190, 210, 235))
            surface.blit(summary, (rect.x + 10, y))
            y += summary.get_height() + 2
        y += 6
        context_label = self.small_font.render("Context:", True, (170, 190, 220))
        surface.blit(context_label, (rect.x + 10, y))
        y += context_label.get_height() + 2
        context_value = self.small_font.render(
            f"  {self._spell_context_list(spell.context)}",
            True,
            (170, 190, 220),
        )
        surface.blit(context_value, (rect.x + 10, y))
        y += context_value.get_height() + 4
        target_line = self.small_font.render(
            f"Target: {'Enemy' if spell.targeted else 'Self/Utility'}",
            True,
            (170, 190, 220),
        )
        surface.blit(target_line, (rect.x + 10, y))
        y += target_line.get_height() + 2
        range_line = self.small_font.render(
            f"Range: {spell.range_tiles}",
            True,
            (170, 190, 220),
        )
        surface.blit(range_line, (rect.x + 10, y))
        y += range_line.get_height() + 8
        context_ok = self._context_available(session, spell)
        reagent_ok = all(session.party.reagents.get(reagent, 0) >= qty for reagent, qty in spell.reagents.items())
        castable = context_ok and reagent_ok
        cast_status = (
            "Can cast now"
            if castable
            else "Wrong context"
            if not context_ok and reagent_ok
            else "Missing reagents"
            if context_ok and not reagent_ok
            else "Wrong context + missing reagents"
        )
        cast_line = self.menu_font.render(
            cast_status,
            True,
            (170, 235, 170) if castable else (255, 140, 140),
        )
        surface.blit(cast_line, (rect.x + 10, y))
        y += cast_line.get_height() + 8

        reag_title = self.menu_font.render("Required Reagents", True, (200, 220, 240))
        surface.blit(reag_title, (rect.x + 10, y))
        y += reag_title.get_height() + 4
        icon_size = 20
        row_h = 26
        if not spell.reagents:
            none = self.small_font.render("None", True, (170, 180, 200))
            surface.blit(none, (rect.x + 10, y))
            return
        for reagent, required in sorted(spell.reagents.items()):
            if y + row_h > rect.bottom - 10:
                break
            available = session.party.reagents.get(reagent, 0)
            color = (170, 220, 180) if available >= required else (255, 125, 125)
            icon = pygame.transform.scale(
                self.atlas.get(self._reagent_sprite_key(reagent)),
                (icon_size, icon_size),
            )
            surface.blit(icon, (rect.x + 10, y + 2))
            text = self.small_font.render(
                f"{self._pretty_reagent_name(reagent)}: {required} ({available})",
                True,
                color,
            )
            surface.blit(text, (rect.x + 10 + icon_size + 8, y + 3))
            y += row_h

    def spellbook_hit_test(self, ui_pos: tuple[int, int], session: GameSession) -> tuple[str, int | None] | None:
        panel = self.SPELLBOOK_PANEL
        if not panel.collidepoint(ui_pos):
            return None
        for tab_id, tab_rect in self._spellbook_tab_rects().items():
            if tab_rect.collidepoint(ui_pos):
                return (f"tab:{tab_id}", None)
        for key, rect in self._spellbook_button_rects().items():
            if rect.collidepoint(ui_pos):
                return (key, None)
        list_rect = self._spellbook_list_rect()
        if not list_rect.collidepoint(ui_pos):
            return ("panel", None)
        entries, _available_count = self._known_spells(session)
        if not entries:
            return ("panel", None)
        row_h = 24
        header_h = 24
        selected_idx = max(0, min(session.spellbook_selected_index, len(entries) - 1))
        visible_rows = max(1, (list_rect.height - header_h - 4) // row_h)
        start_idx = self._spellbook_start_index(len(entries), selected_idx, visible_rows)
        row = (ui_pos[1] - list_rect.y - header_h - 2) // row_h
        index = start_idx + max(0, row)
        if 0 <= row < visible_rows and index < len(entries):
            return ("spell", index)
        return ("panel", None)

    def _spellbook_list_rect(self) -> pygame.Rect:
        panel = self.SPELLBOOK_PANEL
        return pygame.Rect(panel.x + 16, panel.y + 124, 440, panel.height - 200)

    def _spellbook_detail_rect(self) -> pygame.Rect:
        panel = self.SPELLBOOK_PANEL
        return pygame.Rect(panel.x + 470, panel.y + 124, panel.width - 486, panel.height - 200)

    def _spellbook_button_rects(self) -> dict[str, pygame.Rect]:
        panel = self.SPELLBOOK_PANEL
        y = panel.bottom - 56
        return {
            "cast": pygame.Rect(panel.x + 20, y, 180, 36),
            "set": pygame.Rect(panel.x + 220, y, 220, 36),
            "close": pygame.Rect(panel.right - 160, y, 140, 36),
        }

    def _spellbook_tab_rects(self) -> dict[str, pygame.Rect]:
        panel = self.SPELLBOOK_PANEL
        x = panel.x + 16
        y = panel.y + 80
        tab_w = 130
        tab_h = 32
        gap = 8
        rects: dict[str, pygame.Rect] = {}
        for tab_id, _label in self.SPELLBOOK_TABS:
            width = 190 if tab_id == "missing" else tab_w
            rects[tab_id] = pygame.Rect(x, y, width, tab_h)
            x += width + gap
        return rects

    def _draw_spellbook_tabs(self, surface: pygame.Surface, session: GameSession) -> None:
        for tab_id, label in self.SPELLBOOK_TABS:
            rect = self._spellbook_tab_rects()[tab_id]
            active = session.spellbook_tab == tab_id
            fill = (78, 102, 148) if active else (44, 54, 80)
            border = (220, 230, 255) if active else (125, 140, 180)
            pygame.draw.rect(surface, fill, rect)
            pygame.draw.rect(surface, border, rect, 2 if active else 1)
            txt = self.small_font.render(label, True, (245, 250, 255) if active else (190, 205, 235))
            tx = rect.x + (rect.width - txt.get_width()) // 2
            ty = rect.y + (rect.height - txt.get_height()) // 2
            surface.blit(txt, (tx, ty))

    def _spellbook_start_index(self, total: int, selected_idx: int, visible_rows: int) -> int:
        return max(0, min(selected_idx - visible_rows // 2, max(0, total - visible_rows)))

    def _known_spells(self, session: GameSession) -> tuple[list[dict[str, object]], int]:
        known = [spell for spell_id in session.party.spells_known if (spell := get_spell(spell_id)) is not None]
        tab = session.spellbook_tab
        if tab == "missing":
            known = [
                spell
                for spell in known
                if any(session.party.reagents.get(reagent, 0) < qty for reagent, qty in spell.reagents.items())
            ]
        elif tab in {"any", "town", "world"}:
            known = [spell for spell in known if spell.context == f"context-{tab}"]
        entries: list[dict[str, object]] = []
        for spell in known:
            context_ok = self._context_available(session, spell)
            reagent_ok = all(session.party.reagents.get(reagent, 0) >= qty for reagent, qty in spell.reagents.items())
            status = "ready" if context_ok and reagent_ok else "context" if not context_ok else "reagents"
            entries.append({"spell": spell, "status": status})
        available = [entry for entry in entries if entry["status"] == "ready"]
        missing = [entry for entry in entries if entry["status"] != "ready"]
        return available + missing, len(available)

    def _can_cast_spell(self, session: GameSession, spell) -> bool:
        return self._context_available(session, spell) and all(
            session.party.reagents.get(reagent, 0) >= qty for reagent, qty in spell.reagents.items()
        )

    def _context_available(self, session: GameSession, spell) -> bool:
        current_context = getattr(session.place, "spell_context", "context-town")
        return spell_context_available(spell.context, current_context)

    def _spell_summary_text(self, spell) -> str:
        if spell.effect_kind == "attack":
            return "Offensive arcana that damages a single target."
        if spell.effect_kind == "heal":
            return "Restoration spell that recovers party health."
        if spell.effect_kind == "ward":
            return "Defensive ward that reduces incoming damage."
        return "Utility spell with contextual world interactions."

    def _spell_context_list(self, context: str) -> str:
        normalized = context.replace("context-", "").replace("_", "-")
        parts = [part.strip() for part in normalized.split(",") if part.strip()]
        if not parts:
            return "Anywhere"
        pretty = [part.replace("-", " ").title() for part in parts]
        pretty = ["Anywhere" if part == "Any" else part for part in pretty]
        return ", ".join(pretty)

    def _spell_sprite_key(self, spell) -> str:
        icon_key = getattr(spell, "icon_sprite", None)
        if isinstance(icon_key, str) and icon_key and self.atlas.has_key(icon_key):
            return icon_key
        return "s_gem"

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

    def _reagent_sprite_key(self, reagent_id: str) -> str:
        reagent_item = Item(
            item_id=f"t_{reagent_id}",
            name=self._pretty_reagent_name(reagent_id),
            value=0,
        )
        return item_sprite_key(reagent_item, self.atlas.has_key)
