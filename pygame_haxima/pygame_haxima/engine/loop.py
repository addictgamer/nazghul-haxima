from __future__ import annotations

import random
from pathlib import Path

from pygame_haxima.data.content_registry import ContentRegistry
from pygame_haxima.data.quest_engine import QuestEngine
from pygame_haxima.data.save_manager import SaveManager
from pygame_haxima.domain.models import Chest, Entity, GameSession, Mode, TileField, Trap
from pygame_haxima.engine.audio import AudioManager
from pygame_haxima.engine.events import EngineEvent, EngineEventType
from pygame_haxima.engine.renderer import Renderer
from pygame_haxima.engine.spells import get_spell, spell_context_available

HEAL_SPELL_IDS = {"heal", "mani", "vas_mani"}
WARD_SPELL_IDS = {"ward", "sanct_nox", "vas_sanct_nox", "in_flam_sanct", "in_sanct"}
LIGHT_SPELL_IDS = {"in_lor", "vas_lor"}


class TurnLoop:
    def __init__(
        self,
        renderer: Renderer,
        audio: AudioManager,
        save_manager: SaveManager,
        quest_engine: QuestEngine | None = None,
        content_registry: ContentRegistry | None = None,
    ) -> None:
        self.renderer = renderer
        self.audio = audio
        self.save_manager = save_manager
        project_root = Path(__file__).resolve().parents[2]
        converted = project_root / "converted_data"
        self.quest_engine = quest_engine or QuestEngine.load(converted)
        self.content_registry = content_registry

    def process_events(self, session: GameSession, events: list[EngineEvent]) -> None:
        for event in events:
            if event.kind == EngineEventType.QUIT:
                session.running = False
                return
            if event.kind == EngineEventType.ANIMATION_TICK:
                self._tick_feedback(session)
                continue
            if event.kind == EngineEventType.MOUSE_CLICK:
                if session.show_save_load_menu:
                    self._handle_save_load_menu_click(session, event.payload["ui_pos"])
                    continue
                if session.show_spellbook_menu:
                    self._handle_spellbook_menu_click(session, event.payload["ui_pos"])
                continue
            if event.kind == EngineEventType.MOUSE_MOVE:
                if session.show_spellbook_menu:
                    self._handle_spellbook_menu_hover(session, event.payload["ui_pos"])
                continue
            if event.kind == EngineEventType.MOUSE_WHEEL:
                if session.show_spellbook_menu:
                    self._handle_spellbook_menu_scroll(session, int(event.payload.get("y", 0)))
                continue
            if event.kind == EngineEventType.MOUSE_TILE:
                if (
                    session.show_save_load_menu
                    or session.show_options_menu
                    or session.show_reagents_menu
                    or session.show_spellbook_menu
                ):
                    continue
                self._handle_mouse_move(session, event.payload["tile"])
                continue
            if event.kind != EngineEventType.ACTION:
                continue
            action = event.payload["action"]
            if session.show_save_load_menu:
                self._handle_save_load_menu_action(session, action)
                continue
            if session.show_reagents_menu:
                if action in {"cancel", "reagents_menu"}:
                    self._toggle_reagents_menu(session)
                elif action == "spellbook_menu":
                    self._toggle_reagents_menu(session)
                    self._toggle_spellbook_menu(session)
                continue
            if session.show_spellbook_menu:
                self._handle_spellbook_menu_action(session, action)
                continue
            if action == "options_menu":
                self._toggle_options_menu(session)
                continue
            if action == "reagents_menu":
                self._toggle_reagents_menu(session)
                continue
            if action == "spellbook_menu":
                self._toggle_spellbook_menu(session)
                continue
            if session.show_options_menu:
                self._handle_options_menu_action(session, action)
                continue
            if session.targeting_action is not None:
                self._handle_targeting_action(session, action)
                continue
            if action in {"move_n", "move_s", "move_w", "move_e"}:
                dx, dy = {
                    "move_n": (0, -1),
                    "move_s": (0, 1),
                    "move_w": (-1, 0),
                    "move_e": (1, 0),
                }[action]
                self._move_party(session, dx, dy)
            elif action == "talk":
                self._start_targeting(session, "talk", "Talk-<target>(Enter confirm, Esc cancel)")
            elif action == "open":
                self._start_targeting(session, "open", "Open-<target>(Enter confirm, Esc cancel)")
            elif action == "get":
                self._get_items(session)
            elif action == "attack":
                self._start_targeting(session, "attack", "Attack-<target>(Enter confirm, Esc cancel)")
            elif action == "cast":
                self._start_cast(session)
            elif action == "cycle_spell":
                self._cycle_spell(session)
            elif action == "examine":
                self._start_targeting(session, "examine", "Xamine-<target>(Enter confirm, Esc cancel)")
            elif action == "save":
                self._open_save_load_menu(session, "save")
            elif action == "load":
                self._open_save_load_menu(session, "load")
            elif action == "help":
                self._help(session)
            elif action == "travel_zone":
                self._travel_zone(session)
            elif action == "cancel":
                self._end_targeting(session)
            elif action == "fullscreen":
                self.renderer.toggle_fullscreen()
                session.option_fullscreen = self.renderer.is_fullscreen
            elif action == "debug_terrain":
                session.debug_terrain_ids = not session.debug_terrain_ids
                state = "ON" if session.debug_terrain_ids else "OFF"
                session.append_log(f"Terrain debug overlay {state}.")
            elif action == "debug_sprite_warnings":
                session.debug_sprite_warnings = not session.debug_sprite_warnings
                state = "ON" if session.debug_sprite_warnings else "OFF"
                session.append_log(f"Sprite warning overlay {state}.")
            elif action == "debug_runtime_state":
                session.debug_runtime_state = not session.debug_runtime_state
                state = "ON" if session.debug_runtime_state else "OFF"
                session.append_log(f"Runtime state debug panel {state}.")

    def _handle_mouse_move(self, session: GameSession, tile: tuple[int, int]) -> None:
        if session.targeting_action is not None:
            if not self._is_tile_in_target_range(session, tile[0], tile[1]):
                session.append_log("You can't perform that action there.")
                return
            session.target_cursor = tile
            self._confirm_target_action(session)
            return
        tx, ty = tile
        dx = 0 if tx == session.party.x else (1 if tx > session.party.x else -1)
        dy = 0 if ty == session.party.y else (1 if ty > session.party.y else -1)
        if abs(tx - session.party.x) > abs(ty - session.party.y):
            dy = 0
        else:
            dx = 0
        self._move_party(session, dx, dy)

    def _move_party(self, session: GameSession, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        ensnare = session.quest_flags.get("buff:ensnare_turns")
        if isinstance(ensnare, int) and ensnare > 0:
            session.append_log("You are ensnared and cannot move.")
            return
        nx, ny = session.party.x + dx, session.party.y + dy
        if not self._party_can_enter_tile(session, nx, ny):
            session.append_log("Blocked.")
            return
        session.party.x, session.party.y = nx, ny
        session.party.members[0].x, session.party.members[0].y = nx, ny
        session.party.members[0].facing = self._facing_from_delta(dx, dy, session.party.members[0].facing)
        self._apply_tile_field_entry(session, nx, ny, session.party.lead(), "You")
        session.advance_turn()
        session.party.food = max(0, session.party.food - 1)
        self._check_auto_combat(session)
        self._npc_turn(session)

    def _get_items(self, session: GameSession) -> None:
        stack = session.place.ground_items.get((session.party.x, session.party.y), [])
        if not stack:
            session.append_log("Nothing here to get.")
            return
        session.party.inventory.extend(stack)
        total_value = sum(item.value for item in stack)
        session.party.gold += total_value // 4
        names = ", ".join(item.name for item in stack)
        session.append_log(f"Got {names}.")
        session.place.ground_items[(session.party.x, session.party.y)] = []
        session.advance_turn()

    def _attack(self, session: GameSession, monster: Entity) -> None:
        self._clear_combat_feedback(session)
        session.mode = Mode.COMBAT
        session.combat.active = True
        session.combat.enemy_ids = [monster.entity_id]
        session.combat.message = f"Engaged {monster.name}"
        self._resolve_combat_round(session, monster)
        if not monster.is_alive():
            session.append_log(f"{monster.name} falls in combat.")
            self._set_feedback(
                session,
                f"{monster.name}: Falls in combat",
                (170, 255, 170),
                world_pos=(monster.x, monster.y),
            )
            session.quest_flags[f"defeated:{monster.entity_id}"] = True
            session.victory = True
            session.mode = Mode.EXPLORE
            session.combat.active = False
            session.combat.enemy_ids = []
            session.combat.message = ""
            return
        self._enemy_counterattack(session, monster)
        if session.party.lead().hp <= 0:
            session.append_log("The Wanderer has fallen. Game over.")
            session.running = False
            return
        session.mode = Mode.EXPLORE
        session.combat.active = False
        session.combat.enemy_ids = []
        session.combat.message = ""
        session.advance_turn()

    def _examine(self, session: GameSession, x: int, y: int) -> None:
        terrain = session.place.terrain_at(x, y)
        session.append_log(f"You are on {terrain.name}.")
        npc = session.place.npc_at(x, y)
        chest = session.place.chest_at(x, y)
        monster = session.place.monster_at(x, y)
        if npc is not None:
            session.append_log(f"You see {npc.name}.")
        if chest is not None and not chest.opened:
            session.append_log("You see a closed chest.")
        if monster is not None:
            session.append_log(f"You see a hostile {monster.name}.")
        if session.party.inventory:
            session.append_log("Inventory: " + ", ".join(item.name for item in session.party.inventory))
        else:
            session.append_log("Inventory is empty.")

    def _help(self, session: GameSession) -> None:
        session.append_log(
            "Move: arrows/WASD | t talk | o open | g get | f attack | c cast | v cycle spell | b spellbook | x examine"
        )
        session.append_log(
            "F5 save | F9 load | R reagents | F6 travel zone | F10 options | F11 fullscreen | F2/F3/F4 debug"
        )
        session.append_log("Target mode: arrows move cursor | Enter confirm | Esc cancel")
        session.append_log("Set HAXIMA_PLACE=cloviskeep to start in converted Cloviskeep.")

    def _travel_zone(self, session: GameSession) -> None:
        if self.content_registry is None:
            session.append_log("Zone travel is unavailable.")
            return
        if session.place.place_id == "tutorial_wilderness":
            self.content_registry.travel_to(session, "cloviskeep")
            return
        self.content_registry.travel_to(session, "tutorial")

    def _toggle_options_menu(self, session: GameSession) -> None:
        if session.show_save_load_menu:
            return
        session.show_options_menu = not session.show_options_menu
        session.option_scale = self.renderer.scale
        session.option_fullscreen = self.renderer.is_fullscreen
        if session.show_options_menu:
            session.command_prompt = "Options> arrows navigate, left/right change, Esc/F10 close"
            session.append_log("Opened options menu.")
        else:
            session.command_prompt = "Command> (H help, F10 options)"
            session.append_log("Closed options menu.")

    def _toggle_reagents_menu(self, session: GameSession) -> None:
        if session.show_save_load_menu:
            return
        if session.show_options_menu:
            self._toggle_options_menu(session)
        if session.show_spellbook_menu:
            self._toggle_spellbook_menu(session)
        session.show_reagents_menu = not session.show_reagents_menu
        if session.show_reagents_menu:
            session.command_prompt = "Reagents> R/Esc close"
            session.append_log("Opened reagents list.")
        else:
            session.command_prompt = "Command> (H help, F10 options)"
            session.append_log("Closed reagents list.")

    def _toggle_spellbook_menu(self, session: GameSession) -> None:
        if session.show_save_load_menu:
            return
        if session.show_options_menu:
            self._toggle_options_menu(session)
        if session.show_reagents_menu:
            self._toggle_reagents_menu(session)
        session.show_spellbook_menu = not session.show_spellbook_menu
        if session.show_spellbook_menu:
            if session.spellbook_tab not in self._spellbook_tabs():
                session.spellbook_tab = "all"
            ordered = self._spellbook_ordered_spell_ids(session)
            if session.party.selected_spell in ordered:
                session.spellbook_selected_index = ordered.index(session.party.selected_spell)
            else:
                session.spellbook_selected_index = 0
            session.spellbook_hover_index = None
            session.command_prompt = "Spellbook> Left/Right tabs, wheel/Up/Down select, Enter set, C cast, B/Esc close"
            session.append_log("Opened spellbook.")
        else:
            session.spellbook_hover_index = None
            session.command_prompt = "Command> (H help, F10 options)"
            session.append_log("Closed spellbook.")

    def _handle_spellbook_menu_action(self, session: GameSession, action: str) -> None:
        known = self._spellbook_ordered_spell_ids(session)
        if action in {"cancel", "spellbook_menu"}:
            self._toggle_spellbook_menu(session)
            return
        if action == "move_w":
            self._cycle_spellbook_tab(session, -1)
            return
        if action in {"move_e", "spellbook_next_tab"}:
            self._cycle_spellbook_tab(session, 1)
            return
        if not known:
            return
        if action == "move_n":
            session.spellbook_selected_index = (session.spellbook_selected_index - 1) % len(known)
            session.spellbook_hover_index = None
            return
        if action == "move_s":
            session.spellbook_selected_index = (session.spellbook_selected_index + 1) % len(known)
            session.spellbook_hover_index = None
            return
        if action == "confirm":
            self._set_selected_spell_from_spellbook(session, session.spellbook_selected_index)
            return
        if action == "cast":
            self._cast_from_spellbook(session)
            return

    def _handle_spellbook_menu_click(self, session: GameSession, ui_pos: tuple[int, int]) -> None:
        hit = self.renderer.text_ui.spellbook_hit_test(ui_pos, session)
        if hit is None:
            return
        target, index = hit
        if target == "spell" and index is not None:
            session.spellbook_selected_index = index
            session.spellbook_hover_index = index
            self._set_selected_spell_from_spellbook(session, index)
            return
        if target.startswith("tab:"):
            self._set_spellbook_tab(session, target.replace("tab:", "", 1))
            return
        if target == "cast":
            self._cast_from_spellbook(session)
            return
        if target == "set":
            self._set_selected_spell_from_spellbook(session, session.spellbook_selected_index)
            return
        if target == "close":
            self._toggle_spellbook_menu(session)

    def _handle_spellbook_menu_hover(self, session: GameSession, ui_pos: tuple[int, int]) -> None:
        hit = self.renderer.text_ui.spellbook_hit_test(ui_pos, session)
        if hit is None:
            session.spellbook_hover_index = None
            return
        target, index = hit
        if target == "spell":
            session.spellbook_hover_index = index
            return
        session.spellbook_hover_index = None

    def _handle_spellbook_menu_scroll(self, session: GameSession, delta_y: int) -> None:
        known = self._spellbook_ordered_spell_ids(session)
        if not known or delta_y == 0:
            return
        hover_index = session.spellbook_hover_index
        if hover_index is not None and 0 <= hover_index < len(known):
            # First wheel tick over an entry snaps the cursor there.
            if hover_index != session.spellbook_selected_index:
                session.spellbook_selected_index = hover_index
                return
        direction = -1 if delta_y > 0 else 1
        base_index = (
            hover_index
            if hover_index is not None and 0 <= hover_index < len(known)
            else session.spellbook_selected_index
        )
        session.spellbook_selected_index = (base_index + direction) % len(known)
        session.spellbook_hover_index = session.spellbook_selected_index

    def _set_selected_spell_from_spellbook(self, session: GameSession, index: int) -> None:
        known = self._spellbook_ordered_spell_ids(session)
        if not known:
            return
        clamped = max(0, min(index, len(known) - 1))
        session.spellbook_selected_index = clamped
        session.party.selected_spell = known[clamped]
        spell = get_spell(session.party.selected_spell)
        if spell is not None:
            session.append_log(f"Prepared spell: {spell.name}.")

    def _cast_from_spellbook(self, session: GameSession) -> None:
        self._set_selected_spell_from_spellbook(session, session.spellbook_selected_index)
        spell = get_spell(session.party.selected_spell)
        if spell is None:
            return
        if not self._is_spell_context_available(session, spell.spell_id):
            session.append_log(f"{spell.name} cannot be cast in this area.")
            return
        if not self._has_reagents_for_spell(session, spell.spell_id):
            reagent_text = ", ".join(f"{name} x{qty}" for name, qty in sorted(spell.reagents.items()))
            session.append_log(f"You lack reagents for {spell.name} ({reagent_text}).")
            return
        self._toggle_spellbook_menu(session)
        self._start_cast(session)

    def _handle_options_menu_action(self, session: GameSession, action: str) -> None:
        option_count = 4
        if action == "cancel":
            self._toggle_options_menu(session)
            return
        if action == "move_n":
            session.options_selected_index = (session.options_selected_index - 1) % option_count
            return
        if action == "move_s":
            session.options_selected_index = (session.options_selected_index + 1) % option_count
            return
        if action not in {"move_w", "move_e", "fullscreen"}:
            return
        option = session.options_selected_index
        if option == 0:
            delta = 1 if action == "move_e" else -1
            self.renderer.set_scale(max(1, min(4, self.renderer.scale + delta)))
            session.option_scale = self.renderer.scale
            session.append_log(f"UI scale set to {self.renderer.scale}x.")
            return
        if option == 1 or action == "fullscreen":
            self.renderer.toggle_fullscreen()
            session.option_fullscreen = self.renderer.is_fullscreen
            state = "ON" if session.option_fullscreen else "OFF"
            session.append_log(f"Fullscreen {state}.")
            return
        if option == 2:
            session.debug_terrain_ids = not session.debug_terrain_ids
            state = "ON" if session.debug_terrain_ids else "OFF"
            session.append_log(f"Terrain debug overlay {state}.")
            return
        if option == 3:
            session.debug_sprite_warnings = not session.debug_sprite_warnings
            state = "ON" if session.debug_sprite_warnings else "OFF"
            session.append_log(f"Sprite warning overlay {state}.")
            return

    def _open_save_load_menu(self, session: GameSession, mode: str) -> None:
        session.show_save_load_menu = True
        session.save_load_mode = mode
        session.save_load_selected_slot = 0
        session.save_slot_labels = self.save_manager.list_slots()
        action_word = "Save" if mode == "save" else "Load"
        session.command_prompt = f"{action_word} Menu> up/down slot, Enter confirm, Esc cancel"

    def _close_save_load_menu(self, session: GameSession) -> None:
        session.show_save_load_menu = False
        session.save_load_mode = None
        session.command_prompt = "Command> (H help, F10 options)"

    def _handle_save_load_menu_action(self, session: GameSession, action: str) -> None:
        if action == "cancel":
            self._close_save_load_menu(session)
            session.append_log("Closed save/load menu.")
            return
        if action == "save":
            session.save_load_mode = "save"
            session.command_prompt = "Save Menu> up/down slot, Enter confirm, Esc cancel"
            return
        if action == "load":
            session.save_load_mode = "load"
            session.command_prompt = "Load Menu> up/down slot, Enter confirm, Esc cancel"
            return
        if action == "move_n":
            count = max(1, len(session.save_slot_labels))
            session.save_load_selected_slot = (session.save_load_selected_slot - 1) % count
            return
        if action == "move_s":
            count = max(1, len(session.save_slot_labels))
            session.save_load_selected_slot = (session.save_load_selected_slot + 1) % count
            return
        if action != "confirm":
            return

        slot = session.save_load_selected_slot
        mode = session.save_load_mode or "save"
        if mode == "save":
            path = self.save_manager.save_slot(slot, session)
            session.append_log(f"Saved game to {path.name}.")
            session.save_slot_labels = self.save_manager.list_slots()
            return

        loaded = self.save_manager.load_slot(slot, session)
        if loaded:
            self._post_load_sync(session)
            session.append_log("Loaded saved game.")
            self._close_save_load_menu(session)
            return
        if self.save_manager.last_error == "corrupt_save":
            session.append_log("Save file was corrupted and has been quarantined.")
        elif self.save_manager.last_error == "invalid_schema":
            session.append_log("Save file schema is invalid for this build.")
        else:
            session.append_log("No saved game found in that slot.")

    def _post_load_sync(self, session: GameSession) -> None:
        self.renderer.set_scale(max(1, min(4, session.option_scale)))
        if session.option_fullscreen != self.renderer.is_fullscreen:
            self.renderer.toggle_fullscreen()
        session.option_scale = self.renderer.scale
        session.option_fullscreen = self.renderer.is_fullscreen
        session.save_slot_labels = self.save_manager.list_slots()

    def _handle_save_load_menu_click(self, session: GameSession, ui_pos: tuple[int, int]) -> None:
        hit = self.renderer.text_ui.save_load_hit_test(ui_pos, session)
        if hit is None:
            return
        target, index = hit
        if target == "slot" and index is not None:
            session.save_load_selected_slot = index
            return
        if target == "mode_save":
            self._handle_save_load_menu_action(session, "save")
            return
        if target == "mode_load":
            self._handle_save_load_menu_action(session, "load")
            return
        if target == "close":
            self._handle_save_load_menu_action(session, "cancel")
            return
        if target == "confirm":
            self._handle_save_load_menu_action(session, "confirm")

    def _start_targeting(self, session: GameSession, action: str, prompt: str) -> None:
        if action in {"talk", "open", "attack"} and not self._has_action_target_in_range(session, action):
            session.append_log("You can't perform that action right now.")
            return
        session.targeting_action = action
        session.target_cursor = self._default_target_for_action(session, action)
        session.command_prompt = prompt

    def _start_cast(self, session: GameSession) -> None:
        spell = get_spell(session.party.selected_spell)
        if spell is None:
            session.append_log("No spell is currently selected.")
            return
        if not self._is_spell_context_available(session, spell.spell_id):
            session.append_log(f"{spell.name} cannot be cast in this area.")
            return
        if not self._has_reagents_for_spell(session, spell.spell_id):
            reagent_text = ", ".join(
                f"{name} x{qty}" for name, qty in sorted(spell.reagents.items())
            )
            session.append_log(f"You lack reagents for {spell.name} ({reagent_text}).")
            return
        if spell.targeted:
            action = f"cast_{spell.spell_id}"
            if not self._has_action_target_in_range(session, action):
                session.append_log("No valid spell target in range.")
                return
            session.targeting_action = action
            session.target_cursor = self._default_target_for_action(session, action)
            session.command_prompt = f"Cast {spell.name}-<target>(Enter confirm, Esc cancel)"
            return
        self._cast_non_targeted_spell(session, spell)

    def _cycle_spell(self, session: GameSession) -> None:
        known = self._castable_spell_ids(session)
        if not known:
            session.append_log("No castable spells in current context/reagents.")
            return
        if session.party.selected_spell not in known:
            session.party.selected_spell = known[0]
        else:
            idx = known.index(session.party.selected_spell)
            session.party.selected_spell = known[(idx + 1) % len(known)]
        spell = get_spell(session.party.selected_spell)
        if spell is None:
            return
        reagent_text = ", ".join(
            f"{name}:{session.party.reagents.get(name, 0)}" for name in sorted(spell.reagents)
        )
        session.append_log(f"Selected spell: {spell.name} ({reagent_text}).")

    def _castable_spell_ids(self, session: GameSession) -> list[str]:
        known = [spell_id for spell_id in session.party.spells_known if get_spell(spell_id) is not None]
        return [spell_id for spell_id in known if self._is_spell_castable_now(session, spell_id)]

    def _spellbook_ordered_spell_ids(self, session: GameSession) -> list[str]:
        known = [spell_id for spell_id in session.party.spells_known if get_spell(spell_id) is not None]
        tab = session.spellbook_tab
        if tab == "missing":
            return [spell_id for spell_id in known if not self._has_reagents_for_spell(session, spell_id)]
        if tab in {"any", "town", "world"}:
            context_tag = f"context-{tab}"
            known = [
                spell_id
                for spell_id in known
                if (spell := get_spell(spell_id)) is not None and spell.context == context_tag
            ]
        available = [spell_id for spell_id in known if self._is_spell_castable_now(session, spell_id)]
        available_set = set(available)
        missing = [spell_id for spell_id in known if spell_id not in available_set]
        return available + missing

    def _spellbook_tabs(self) -> list[str]:
        return ["all", "any", "town", "world", "missing"]

    def _cycle_spellbook_tab(self, session: GameSession, direction: int) -> None:
        tabs = self._spellbook_tabs()
        current = session.spellbook_tab if session.spellbook_tab in tabs else "all"
        idx = tabs.index(current)
        self._set_spellbook_tab(session, tabs[(idx + direction) % len(tabs)])

    def _set_spellbook_tab(self, session: GameSession, tab: str) -> None:
        if tab not in self._spellbook_tabs():
            return
        session.spellbook_tab = tab
        session.spellbook_hover_index = None
        ordered = self._spellbook_ordered_spell_ids(session)
        if session.party.selected_spell in ordered:
            session.spellbook_selected_index = ordered.index(session.party.selected_spell)
        else:
            session.spellbook_selected_index = 0

    def _is_spell_context_available(self, session: GameSession, spell_id: str) -> bool:
        spell = get_spell(spell_id)
        if spell is None:
            return False
        current_context = getattr(session.place, "spell_context", "context-town")
        return spell_context_available(spell.context, current_context)

    def _is_spell_castable_now(self, session: GameSession, spell_id: str) -> bool:
        return self._is_spell_context_available(session, spell_id) and self._has_reagents_for_spell(
            session, spell_id
        )

    def _end_targeting(self, session: GameSession) -> None:
        session.targeting_action = None
        session.target_cursor = None
        session.command_prompt = "Command> (H help, F10 options)"

    def _handle_targeting_action(self, session: GameSession, action: str) -> None:
        if action in {"move_n", "move_s", "move_w", "move_e"}:
            dx, dy = {
                "move_n": (0, -1),
                "move_s": (0, 1),
                "move_w": (-1, 0),
                "move_e": (1, 0),
            }[action]
            self._move_target_cursor(session, dx, dy)
            return
        if action == "confirm":
            self._confirm_target_action(session)
            return
        if action == "cancel":
            self._end_targeting(session)
            return

    def _move_target_cursor(self, session: GameSession, dx: int, dy: int) -> None:
        if session.target_cursor is None:
            session.target_cursor = (session.party.x, session.party.y)
        x, y = session.target_cursor
        nx = max(0, min(session.place.width - 1, x + dx))
        ny = max(0, min(session.place.height - 1, y + dy))
        if not self._is_tile_in_target_range(session, nx, ny):
            return
        session.target_cursor = (nx, ny)

    def _confirm_target_action(self, session: GameSession) -> None:
        if session.targeting_action is None or session.target_cursor is None:
            return
        x, y = session.target_cursor
        action = session.targeting_action
        if action == "talk":
            npc = session.place.npc_at(x, y)
            if npc is None:
                session.append_log("No one there to talk to.")
                return
            if self._distance_from_party(session, x, y) > 1:
                session.append_log("You can't perform that action there.")
                return
            session.mode = Mode.TALK
            npc_state = session.npc_states.setdefault(npc.npc_id, {})
            talk_count = int(npc_state.get("talk_count", 0)) + 1
            npc_state["talk_count"] = talk_count
            npc_state["last_turn"] = session.party.turn_count
            session.quest_flags[f"talked:{npc.npc_id}"] = True
            self.quest_engine.on_talk(session, npc.npc_id)
            line_name = npc.keywords.get("name", "Greetings.")
            line_job = npc.keywords.get("job", "I wander.")
            line_bye = npc.keywords.get("bye", "Farewell.")
            if talk_count > 1:
                line_name = f"Welcome back. {line_name}"
            session.dialogue_speaker = npc.name
            session.dialogue_lines = [line_name, line_job, line_bye]
            session.append_log(f"{npc.name}: {line_name}")
            session.append_log(f"{npc.name}: {line_job}")
            session.append_log(f"{npc.name}: {line_bye}")
            session.mode = Mode.EXPLORE
            session.advance_turn()
            self._end_targeting(session)
            return
        if action == "open":
            chest = session.place.chest_at(x, y)
            if chest is None:
                session.append_log("No chest there.")
                return
            if self._distance_from_party(session, x, y) > 1:
                session.append_log("You can't perform that action there.")
                return
            if chest.opened:
                session.append_log("Chest is already open.")
                self._end_targeting(session)
                return
            chest.opened = True
            if chest.items:
                session.place.ground_items[(chest.x, chest.y)] = list(chest.items)
            session.quest_flags[f"opened:{chest.chest_id}"] = True
            self.quest_engine.on_chest_opened(session, chest.chest_id)
            session.append_log("You open the chest. Items spill onto the ground.")
            session.advance_turn()
            self._end_targeting(session)
            return
        if action == "attack":
            monster = session.place.monster_at(x, y)
            if monster is None:
                session.append_log("No enemy there.")
                return
            if self._distance_from_party(session, x, y) > 1:
                session.append_log("You can't perform that action there.")
                return
            self._attack(session, monster)
            self._end_targeting(session)
            return
        cast_spell_id = self._cast_spell_id(action)
        if cast_spell_id is not None:
            spell = get_spell(cast_spell_id)
            if spell is None:
                return
            if self._distance_from_party(session, x, y) > spell.range_tiles:
                session.append_log("You can't cast that far.")
                return
            if not self._has_reagents_for_spell(session, cast_spell_id):
                session.append_log(f"You lack reagents for {spell.name}.")
                self._end_targeting(session)
                return
            if spell.effect_kind in {"blink", "teleport", "gate"}:
                if not self._is_blink_target_tile(session, x, y):
                    session.append_log("Blink failed: impassable terrain.")
                    return
                self._cast_blink_spell(session, spell, x, y)
                return
            if spell.effect_kind == "telekinesis":
                self._cast_telekinesis(session, spell, x, y)
                self._end_targeting(session)
                return
                self._end_targeting(session)
                return
            monster = session.place.monster_at(x, y)
            if monster is None:
                session.append_log("No enemy there to cast at.")
                return
            self._cast_targeted_spell(session, spell, monster)
            self._end_targeting(session)
            return
        if action == "examine":
            self._examine(session, x, y)
            self._end_targeting(session)

    def _distance_from_party(self, session: GameSession, x: int, y: int) -> int:
        return abs(session.party.x - x) + abs(session.party.y - y)

    def _is_tile_in_target_range(self, session: GameSession, x: int, y: int) -> bool:
        if session.targeting_action in {"talk", "open", "attack"}:
            return self._distance_from_party(session, x, y) <= 1
        cast_spell_id = self._cast_spell_id(session.targeting_action)
        if cast_spell_id is not None:
            spell = get_spell(cast_spell_id)
            if spell is not None:
                return self._distance_from_party(session, x, y) <= spell.range_tiles
        return True

    def _has_action_target_in_range(self, session: GameSession, action: str) -> bool:
        px, py = session.party.x, session.party.y
        candidates = [(px, py), (px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)]
        if action == "talk":
            return any(session.place.npc_at(x, y) is not None for x, y in candidates)
        if action == "open":
            return any(session.place.chest_at(x, y) is not None for x, y in candidates)
        if action == "attack":
            return any(session.place.monster_at(x, y) is not None for x, y in candidates)
        cast_spell_id = self._cast_spell_id(action)
        if cast_spell_id is not None:
            spell = get_spell(cast_spell_id)
            if spell is None or not spell.targeted:
                return False
            targeted_tiles = self._tiles_in_range(px, py, spell.range_tiles)
            if spell.effect_kind in {"blink", "teleport", "gate"}:
                return any(
                    self._is_blink_target_tile(session, x, y) and (x, y) != (px, py)
                    for x, y in targeted_tiles
                )
            if spell.effect_kind == "telekinesis":
                return any(
                    self._is_telekinesis_target(session, x, y) for x, y in targeted_tiles
                )
            return any(session.place.monster_at(x, y) is not None for x, y in targeted_tiles)
        return True

    def _default_target_for_action(self, session: GameSession, action: str) -> tuple[int, int]:
        px, py = session.party.x, session.party.y
        candidates = [(px, py), (px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)]
        if action == "talk":
            matches = [(x, y) for x, y in candidates if session.place.npc_at(x, y) is not None]
            return matches[0] if matches else (px, py)
        if action == "open":
            matches = [(x, y) for x, y in candidates if session.place.chest_at(x, y) is not None]
            return matches[0] if matches else (px, py)
        if action == "attack":
            matches = [(x, y) for x, y in candidates if session.place.monster_at(x, y) is not None]
            return matches[0] if matches else (px, py)
        cast_spell_id = self._cast_spell_id(action)
        if cast_spell_id is not None:
            spell = get_spell(cast_spell_id)
            if spell is None or not spell.targeted:
                return px, py
            extended = self._tiles_in_range(px, py, spell.range_tiles)
            if spell.effect_kind in {"blink", "teleport", "gate"}:
                matches = [
                    (x, y)
                    for x, y in extended
                    if self._is_blink_target_tile(session, x, y) and (x, y) != (px, py)
                ]
                return matches[0] if matches else (px, py)
            if spell.effect_kind == "telekinesis":
                matches = [
                    (x, y) for x, y in extended if self._is_telekinesis_target(session, x, y)
                ]
                return matches[0] if matches else (px, py)
            matches = [(x, y) for x, y in extended if session.place.monster_at(x, y) is not None]
            return matches[0] if matches else (px, py)
        return px, py

    def _tiles_in_range(self, x: int, y: int, range_tiles: int) -> list[tuple[int, int]]:
        tiles: list[tuple[int, int]] = []
        for dx in range(-range_tiles, range_tiles + 1):
            for dy in range(-range_tiles, range_tiles + 1):
                if abs(dx) + abs(dy) <= range_tiles:
                    tiles.append((x + dx, y + dy))
        return tiles

    def _cast_spark(self, session: GameSession, monster: Entity) -> None:
        self._consume_reagents(session, "spark")
        damage = random.randint(2, 5)
        monster.hp = max(0, monster.hp - damage)
        session.append_log(f"You cast Spark on {monster.name} for {damage} damage.")
        self._clear_combat_feedback(session)
        self._set_feedback(session, f"You: Spark {damage}", (170, 210, 255), world_pos=(monster.x, monster.y))
        if not monster.is_alive():
            session.append_log(f"{monster.name} is incinerated.")
            self._set_feedback(
                session, f"{monster.name}: Incinerated", (200, 255, 180), world_pos=(monster.x, monster.y)
            )
            session.quest_flags[f"defeated:{monster.entity_id}"] = True
            session.victory = True
            session.advance_turn()
            return
        if self._distance_from_party(session, monster.x, monster.y) <= 1:
            self._enemy_counterattack(session, monster)
        session.advance_turn()

    def _cast_heal(
        self,
        session: GameSession,
        spell_id: str = "heal",
        spell_name: str = "Heal",
        min_heal: int = 3,
        max_heal: int = 6,
    ) -> None:
        caster = session.party.lead()
        if caster.hp >= caster.max_hp:
            session.append_log("You are already at full health.")
            return
        self._consume_reagents(session, spell_id)
        heal = random.randint(min_heal, max_heal)
        caster.hp = min(caster.max_hp, caster.hp + heal)
        session.append_log(f"You cast {spell_name} and recover {heal} HP.")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name} {heal}", (170, 255, 200), world_pos=(session.party.x, session.party.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_targeted_spell(self, session: GameSession, spell, monster: Entity) -> None:
        if spell.spell_id == "spark":
            self._cast_spark(session, monster)
            return
        if spell.effect_kind == "field":
            self._cast_field_spell(session, spell, monster)
            return
        if spell.effect_kind == "sleep":
            self._cast_sleep_targeted(session, spell, monster)
            return
        if spell.effect_kind == "poison":
            self._cast_poison_targeted(session, spell, monster)
            return
        if spell.effect_kind == "charm":
            self._cast_charm_targeted(session, spell, monster)
            return
        if spell.effect_kind == "web":
            self._cast_web_targeted(session, spell, monster)
            return
        if spell.effect_kind == "illusion":
            self._cast_illusion_targeted(session, spell, monster)
            return
        if spell.effect_kind == "clone":
            self._cast_clone_targeted(session, spell, monster)
            return
        self._consume_reagents(session, spell.spell_id)
        damage = random.randint(1 + spell.circle, 2 + spell.circle * 2)
        monster.hp = max(0, monster.hp - damage)
        session.append_log(f"You cast {spell.name} on {monster.name} for {damage} damage.")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell.name} {damage}", (170, 210, 255), world_pos=(monster.x, monster.y)
        )
        if not monster.is_alive():
            session.append_log(f"{monster.name} is defeated.")
            self._set_feedback(
                session, f"{monster.name}: Falls", (200, 255, 180), world_pos=(monster.x, monster.y)
            )
            session.quest_flags[f"defeated:{monster.entity_id}"] = True
            session.victory = True
            session.advance_turn()
            return
        if self._distance_from_party(session, monster.x, monster.y) <= 1:
            self._enemy_counterattack(session, monster)
        session.advance_turn()

    def _cast_field_spell(self, session: GameSession, spell, center: Entity) -> None:
        self._consume_reagents(session, spell.spell_id)
        targets = [
            monster
            for monster in session.place.monsters
            if monster.is_alive() and abs(monster.x - center.x) + abs(monster.y - center.y) <= 1
        ]
        if not targets:
            session.append_log(f"You cast {spell.name}, but the field catches nothing.")
            field_kind = self._field_kind_for_spell(spell.spell_id, spell.name)
            field_turns = max(4, min(12, spell.circle + 3))
            placed = self._place_field_tiles(session, center.x, center.y, field_kind, field_turns)
            if placed:
                session.append_log(f"{spell.name} lingers on {placed} tile(s) ({field_turns} turns).")
            self._clear_combat_feedback(session)
            self._set_feedback(
                session, f"You: {spell.name}", (255, 205, 160), world_pos=(center.x, center.y)
            )
            if self._distance_from_party(session, center.x, center.y) <= 1:
                self._enemy_counterattack(session, center)
            session.advance_turn()
            return
        hit_count = 0
        for monster in targets:
            damage = random.randint(max(2, spell.circle), max(4, spell.circle + 2))
            monster.hp = max(0, monster.hp - damage)
            hit_count += 1
            session.append_log(f"{spell.name} scorches {monster.name} for {damage}.")
            if not monster.is_alive():
                session.append_log(f"{monster.name} is defeated.")
                session.quest_flags[f"defeated:{monster.entity_id}"] = True
        session.victory = all(not monster.is_alive() for monster in session.place.monsters)
        field_kind = self._field_kind_for_spell(spell.spell_id, spell.name)
        field_turns = max(4, min(12, spell.circle + 3))
        placed = self._place_field_tiles(session, center.x, center.y, field_kind, field_turns)
        if placed:
            session.append_log(f"{spell.name} lingers on {placed} tile(s) ({field_turns} turns).")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell.name} x{hit_count}", (255, 190, 145), world_pos=(center.x, center.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_non_targeted_spell(self, session: GameSession, spell) -> None:
        if spell.spell_id in HEAL_SPELL_IDS or spell.effect_kind == "heal":
            self._cast_heal(
                session,
                spell_id=spell.spell_id,
                spell_name=spell.name,
                min_heal=max(3, spell.circle + 1),
                max_heal=max(6, spell.circle * 2 + 2),
            )
            return
        if spell.spell_id in WARD_SPELL_IDS or spell.effect_kind == "ward":
            charges = 2 if spell.spell_id == "ward" else max(1, min(5, spell.circle // 2 + 1))
            self._cast_ward(
                session,
                spell_id=spell.spell_id,
                spell_name=spell.name,
                added_charges=charges,
                max_charges=8,
            )
            return
        if spell.spell_id in LIGHT_SPELL_IDS or spell.effect_kind == "light":
            self._consume_reagents(session, spell.spell_id)
            light_turns = 10 if spell.spell_id == "in_lor" else 24
            session.quest_flags["buff:light_turns"] = light_turns + 1
            session.append_log(f"You cast {spell.name}. The area brightens ({light_turns} turns).")
            self._finish_spell_cast(session, spell.name, (235, 235, 150))
            return
        if spell.effect_kind == "locate":
            self._consume_reagents(session, spell.spell_id)
            self._cast_locate(session, spell.name)
            return
        if spell.effect_kind == "unlock":
            self._consume_reagents(session, spell.spell_id)
            self._cast_unlock(session, spell.name)
            return
        if spell.effect_kind == "lock":
            self._consume_reagents(session, spell.spell_id)
            self._cast_lock(session, spell.name)
            return
        if spell.effect_kind == "quickness":
            self._consume_reagents(session, spell.spell_id)
            self._cast_quickness(session, spell.name, spell.circle)
            return
        if spell.effect_kind == "sight":
            self._consume_reagents(session, spell.spell_id)
            self._cast_sight(session, spell.name, spell.circle)
            return
        if spell.effect_kind == "dispel":
            self._consume_reagents(session, spell.spell_id)
            self._cast_dispel(session, spell.name)
            return
        if spell.effect_kind == "dispel_field":
            self._consume_reagents(session, spell.spell_id)
            self._cast_dispel_field(session, spell.name, spell.circle)
            return
        if spell.effect_kind == "sleep_area":
            self._consume_reagents(session, spell.spell_id)
            self._cast_sleep_area(session, spell.name, spell.circle)
            return
        if spell.effect_kind == "awaken":
            self._consume_reagents(session, spell.spell_id)
            self._cast_awaken(session, spell.name, spell.circle)
            return
        if spell.effect_kind == "cure_poison":
            self._consume_reagents(session, spell.spell_id)
            self._cast_cure_poison(session, spell.name, spell.spell_id, spell.circle)
            return
        if spell.effect_kind == "fear":
            self._consume_reagents(session, spell.spell_id)
            self._cast_fear(session, spell.name, spell.circle)
            return
        if spell.effect_kind == "turn_undead":
            self._consume_reagents(session, spell.spell_id)
            self._cast_turn_undead(session, spell.name, spell.circle)
            return
        extra_handlers = {
            "trap_detect": lambda: self._cast_trap_detect(session, spell.name, spell.circle),
            "trap_disarm": lambda: self._cast_trap_disarm(session, spell.name, spell.circle),
            "smoke": lambda: self._cast_smoke(session, spell.name, spell.circle),
            "summon": lambda: self._cast_summon(session, spell),
            "calm_spiders": lambda: self._cast_calm_spiders(session, spell.name, spell.circle),
            "force_field": lambda: self._cast_force_field(session, spell.name, spell.circle),
            "invisibility": lambda: self._cast_invisibility(session, spell.name, spell.circle),
            "confusion": lambda: self._cast_confusion(session, spell.name, spell.circle),
            "wind": lambda: self._cast_wind(session, spell.name),
            "resurrection": lambda: self._cast_resurrection(session, spell.name, spell.circle),
            "time_stop": lambda: self._cast_time_stop(session, spell.name, spell.circle),
            "raise_ship": lambda: self._cast_raise_ship(session, spell.name),
            "tremor": lambda: self._cast_tremor(session, spell.name, spell.circle),
            "cone_poison": lambda: self._cast_cone_spell(session, spell, "poison"),
            "cone_sleep": lambda: self._cast_cone_spell(session, spell, "sleep"),
            "cone_fire": lambda: self._cast_cone_spell(session, spell, "fire"),
        }
        handler = extra_handlers.get(spell.effect_kind)
        if handler is not None:
            self._consume_reagents(session, spell.spell_id)
            handler()
            return
        self._consume_reagents(session, spell.spell_id)
        session.append_log(f"You cast {spell.name}.")
        self._finish_spell_cast(session, spell.name, (175, 220, 255))

    def _cast_locate(self, session: GameSession, spell_name: str) -> None:
        nearest = self._nearest_alive_monster(session)
        if nearest is None:
            session.append_log(f"You cast {spell_name}. You sense no hostile presence.")
            self._clear_combat_feedback(session)
            self._set_feedback(
                session, f"You: {spell_name}", (200, 210, 255), world_pos=(session.party.x, session.party.y)
            )
            session.advance_turn()
            return
        distance = self._distance_from_party(session, nearest.x, nearest.y)
        direction = self._direction_to(session, nearest.x, nearest.y)
        session.append_log(
            f"You cast {spell_name}. Nearest hostile is {nearest.name} to the {direction} ({distance} tiles)."
        )
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name} {direction}", (200, 210, 255), world_pos=(session.party.x, session.party.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_unlock(self, session: GameSession, spell_name: str) -> None:
        chest = self._adjacent_closed_chest(session)
        if chest is None:
            session.append_log(f"You cast {spell_name}. No locked chest is nearby.")
            self._clear_combat_feedback(session)
            self._set_feedback(
                session, f"You: {spell_name}", (210, 210, 255), world_pos=(session.party.x, session.party.y)
            )
            adjacent = self._adjacent_monster(session)
            if adjacent is not None:
                self._enemy_counterattack(session, adjacent)
            session.advance_turn()
            return
        chest.opened = True
        if chest.items:
            session.place.ground_items[(chest.x, chest.y)] = list(chest.items)
        session.quest_flags[f"opened:{chest.chest_id}"] = True
        self.quest_engine.on_chest_opened(session, chest.chest_id)
        session.append_log(f"You cast {spell_name}. The chest clicks open.")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name}", (210, 230, 255), world_pos=(chest.x, chest.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_lock(self, session: GameSession, spell_name: str) -> None:
        chest = self._adjacent_opened_chest(session)
        if chest is None:
            session.append_log(f"You cast {spell_name}. No open chest is nearby.")
            self._clear_combat_feedback(session)
            self._set_feedback(
                session, f"You: {spell_name}", (210, 210, 255), world_pos=(session.party.x, session.party.y)
            )
            adjacent = self._adjacent_monster(session)
            if adjacent is not None:
                self._enemy_counterattack(session, adjacent)
            session.advance_turn()
            return
        chest.opened = False
        session.append_log(f"You cast {spell_name}. The chest seals shut.")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name}", (190, 220, 255), world_pos=(chest.x, chest.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_quickness(self, session: GameSession, spell_name: str, circle: int) -> None:
        duration = max(8, min(24, circle * 3))
        # Add one extra step so the immediate end-of-action advance lands on the displayed duration.
        session.quest_flags["buff:quickness_turns"] = duration + 1
        session.append_log(f"You cast {spell_name}. Your reflexes sharpen ({duration} turns).")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name}", (200, 235, 255), world_pos=(session.party.x, session.party.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_sight(self, session: GameSession, spell_name: str, circle: int) -> None:
        radius = max(4, min(14, 2 + circle * 2))
        hostiles = self._hostiles_in_radius(session, radius)
        chests = self._closed_chests_in_radius(session, radius)

        if not hostiles and not chests:
            session.append_log(f"You cast {spell_name}. Your senses find nothing unusual nearby.")
        else:
            parts: list[str] = []
            if hostiles:
                nearest_monster, nearest_distance = hostiles[0]
                parts.append(
                    f"hostiles {len(hostiles)} (nearest: {nearest_monster.name} {nearest_distance} tiles)"
                )
            if chests:
                nearest_chest, nearest_distance = chests[0]
                parts.append(f"chests {len(chests)} (nearest: {nearest_distance} tiles)")
                session.quest_flags[f"sensed_chest:{nearest_chest.chest_id}"] = True
            session.append_log(f"You cast {spell_name}. Senses: {'; '.join(parts)}.")

        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name}", (210, 225, 255), world_pos=(session.party.x, session.party.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_dispel_field(self, session: GameSession, spell_name: str, circle: int) -> None:
        radius = max(3, min(10, circle + 2))
        cleared = self._clear_tile_fields_in_radius(session, session.party.x, session.party.y, radius)
        if cleared:
            session.append_log(f"You cast {spell_name}. Cleared {cleared} lingering field(s).")
        else:
            session.append_log(f"You cast {spell_name}. No lingering fields nearby.")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name}", (210, 230, 255), world_pos=(session.party.x, session.party.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_dispel(self, session: GameSession, spell_name: str) -> None:
        dispelled: list[str] = []
        if session.party.ward_charges > 0:
            session.party.ward_charges = 0
            dispelled.append("ward")
        party_poison = session.quest_flags.get("buff:poison_turns")
        if isinstance(party_poison, int) and party_poison > 0:
            session.quest_flags.pop("buff:poison_turns", None)
            dispelled.append("poison")
        for buff_key, label in (
            ("buff:light_turns", "light"),
            ("buff:quickness_turns", "quickness"),
        ):
            value = session.quest_flags.get(buff_key)
            if isinstance(value, int) and value > 0:
                session.quest_flags.pop(buff_key, None)
                dispelled.append(label)
        sensed_keys = [key for key in session.quest_flags if key.startswith("sensed_chest:")]
        if sensed_keys:
            for key in sensed_keys:
                session.quest_flags.pop(key, None)
            dispelled.append("sensed traces")
        for prefix, label in (
            ("sleep:", "sleep"),
            ("fear:", "fear"),
            ("charm:", "charm"),
            ("ensnare:", "ensnare"),
            ("confuse:", "confusion"),
        ):
            keys = [key for key in session.quest_flags if key.startswith(prefix)]
            if keys:
                for key in keys:
                    session.quest_flags.pop(key, None)
                dispelled.append(label)
        for buff_key, label in (
            ("buff:invisible_turns", "invisibility"),
            ("buff:ensnare_turns", "ensnare"),
        ):
            value = session.quest_flags.get(buff_key)
            if isinstance(value, int) and value > 0:
                session.quest_flags.pop(buff_key, None)
                dispelled.append(label)
        summon_keys = [key for key in session.quest_flags if key.startswith("summon:")]
        if summon_keys:
            monsters_by_id = {monster.entity_id: monster for monster in session.place.monsters}
            for key in summon_keys:
                entity_id = key.removeprefix("summon:")
                monster = monsters_by_id.get(entity_id)
                if monster is not None and not monster.hostile:
                    monster.hp = 0
                session.quest_flags.pop(key, None)
            dispelled.append("summons")
        monster_poison_keys = [key for key in session.quest_flags if key.startswith("poison:")]
        if monster_poison_keys:
            for key in monster_poison_keys:
                session.quest_flags.pop(key, None)
            dispelled.append("monster poison")
        if dispelled:
            session.append_log(f"You cast {spell_name}. Dispelled: {', '.join(dispelled)}.")
        else:
            session.append_log(f"You cast {spell_name}. No magical effects to dispel.")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name}", (220, 220, 255), world_pos=(session.party.x, session.party.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_ward(
        self,
        session: GameSession,
        spell_id: str = "ward",
        spell_name: str = "Ward",
        added_charges: int = 2,
        max_charges: int = 4,
    ) -> None:
        self._consume_reagents(session, spell_id)
        session.party.ward_charges = min(max_charges, session.party.ward_charges + added_charges)
        session.append_log(
            f"You cast {spell_name}. Incoming damage reduced for {added_charges} hits."
        )
        self._clear_combat_feedback(session)
        self._set_feedback(
            session,
            f"You: {spell_name} +{added_charges}",
            (170, 220, 255),
            world_pos=(session.party.x, session.party.y),
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _check_auto_combat(self, session: GameSession) -> None:
        monster = self._adjacent_monster(session)
        if monster is not None:
            session.append_log(f"A {monster.name} snarls nearby. Press F to attack.")

    def _adjacent_monster(self, session: GameSession) -> Entity | None:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            monster = session.place.monster_at(session.party.x + dx, session.party.y + dy)
            if monster is not None:
                return monster
        return None

    def _adjacent_closed_chest(self, session: GameSession) -> Chest | None:
        px, py = session.party.x, session.party.y
        for x, y in ((px, py), (px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
            chest = session.place.chest_at(x, y)
            if chest is not None and not chest.opened:
                return chest
        return None

    def _adjacent_opened_chest(self, session: GameSession) -> Chest | None:
        px, py = session.party.x, session.party.y
        for x, y in ((px, py), (px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
            chest = session.place.chest_at(x, y)
            if chest is not None and chest.opened:
                return chest
        return None

    def _hostiles_in_radius(self, session: GameSession, radius: int) -> list[tuple[Entity, int]]:
        found: list[tuple[Entity, int]] = []
        for monster in session.place.monsters:
            if not monster.is_alive():
                continue
            distance = self._distance_from_party(session, monster.x, monster.y)
            if distance <= radius:
                found.append((monster, distance))
        found.sort(key=lambda pair: pair[1])
        return found

    def _closed_chests_in_radius(self, session: GameSession, radius: int) -> list[tuple[Chest, int]]:
        found: list[tuple[Chest, int]] = []
        for chest in session.place.chests:
            if chest.opened:
                continue
            distance = self._distance_from_party(session, chest.x, chest.y)
            if distance <= radius:
                found.append((chest, distance))
        found.sort(key=lambda pair: pair[1])
        return found

    def _nearest_alive_monster(self, session: GameSession) -> Entity | None:
        nearest: Entity | None = None
        nearest_distance: int | None = None
        for monster in session.place.monsters:
            if not monster.is_alive():
                continue
            distance = self._distance_from_party(session, monster.x, monster.y)
            if nearest_distance is None or distance < nearest_distance:
                nearest = monster
                nearest_distance = distance
        return nearest

    def _direction_to(self, session: GameSession, x: int, y: int) -> str:
        dx = x - session.party.x
        dy = y - session.party.y
        vertical = "north" if dy < 0 else "south" if dy > 0 else ""
        horizontal = "east" if dx > 0 else "west" if dx < 0 else ""
        if vertical and horizontal:
            return f"{vertical}-{horizontal}"
        if vertical:
            return vertical
        if horizontal:
            return horizontal
        return "here"

    def _resolve_combat_round(self, session: GameSession, monster: Entity) -> None:
        attacker = session.party.lead()
        attack_roll = random.randint(1, 6) + attacker.attack
        defense_roll = random.randint(1, 6) + monster.defense
        if attack_roll <= defense_roll:
            session.append_log(f"You miss the {monster.name}.")
            self._set_feedback(session, "You: Miss", (230, 220, 120), world_pos=(monster.x, monster.y))
            return
        damage = max(1, attack_roll - defense_roll)
        monster.hp = max(0, monster.hp - damage)
        session.append_log(f"You hit {monster.name} for {damage} damage.")
        self._set_feedback(
            session, f"You: Hit {damage}", (255, 170, 140), world_pos=(monster.x, monster.y)
        )
        self.audio.play_effect("sounds/hit.wav")

    def _enemy_counterattack(self, session: GameSession, monster: Entity) -> None:
        if not monster.is_alive():
            return
        if self._monster_sleep_turns(session, monster.entity_id) > 0:
            session.append_log(f"{monster.name} is asleep and cannot attack.")
            return
        if self._monster_charm_turns(session, monster.entity_id) > 0:
            session.append_log(f"{monster.name} is charmed and will not attack.")
            return
        if self._monster_fear_turns(session, monster.entity_id) > 0:
            session.append_log(f"{monster.name} flees in terror and cannot attack.")
            return
        if self._monster_confuse_turns(session, monster.entity_id) > 0 and random.randint(1, 6) <= 3:
            session.append_log(f"{monster.name} is too confused to attack.")
            return
        target = session.party.lead()
        attack_roll = random.randint(1, 6) + monster.attack
        quickness_turns = session.quest_flags.get("buff:quickness_turns")
        quickness_bonus = 2 if isinstance(quickness_turns, int) and quickness_turns > 0 else 0
        defense_roll = random.randint(1, 6) + target.defense + quickness_bonus
        if attack_roll <= defense_roll:
            session.append_log(f"{monster.name} misses.")
            self._set_feedback(
                session,
                f"{monster.name}: Misses",
                (220, 210, 120),
                world_pos=(session.party.x, session.party.y),
            )
            return
        damage = max(1, attack_roll - defense_roll)
        if session.party.ward_charges > 0:
            reduced = damage
            damage = max(1, damage - 2)
            session.party.ward_charges = max(0, session.party.ward_charges - 1)
            blocked = reduced - damage
            if blocked > 0:
                session.append_log(f"Ward absorbs {blocked} damage. Charges left: {session.party.ward_charges}")
        target.hp = max(0, target.hp - damage)
        session.append_log(f"{monster.name} hits you for {damage}. HP: {target.hp}/{target.max_hp}")
        self._set_feedback(
            session,
            f"{monster.name}: Hit {damage}",
            (255, 120, 120),
            world_pos=(session.party.x, session.party.y),
        )

    def _set_feedback(
        self,
        session: GameSession,
        text: str,
        color: tuple[int, int, int],
        ticks: int = 55,
        world_pos: tuple[int, int] | None = None,
    ) -> None:
        if session.combat_feedback_ticks > 0 and session.combat_feedback_text:
            session.combat_feedback_lines.append((text, color))
            session.combat_feedback_text = "\n".join(line for line, _ in session.combat_feedback_lines)
            session.combat_feedback_ticks = max(session.combat_feedback_ticks, ticks)
            if session.combat_feedback_world_pos != world_pos:
                session.combat_feedback_world_pos = None
            return
        session.combat_feedback_lines = [(text, color)]
        session.combat_feedback_text = text
        session.combat_feedback_color = color
        session.combat_feedback_ticks = ticks
        session.combat_feedback_world_pos = world_pos

    def _tick_feedback(self, session: GameSession) -> None:
        session.ui_anim_tick = (session.ui_anim_tick + 1) % 10_000
        if session.combat_feedback_ticks <= 0:
            return
        session.combat_feedback_ticks -= 1
        if session.combat_feedback_ticks == 0:
            self._clear_combat_feedback(session)

    def _clear_combat_feedback(self, session: GameSession) -> None:
        session.combat_feedback_text = None
        session.combat_feedback_ticks = 0
        session.combat_feedback_world_pos = None
        session.combat_feedback_lines = []

    def _npc_turn(self, session: GameSession) -> None:
        # Tiny movement jitter emulates non-player turns in place_exec.
        for monster in session.place.monsters:
            if not monster.is_alive():
                continue
            if self._monster_sleep_turns(session, monster.entity_id) > 0:
                continue
            if self._monster_ensnare_turns(session, monster.entity_id) > 0:
                continue
            if self._monster_charm_turns(session, monster.entity_id) > 0:
                continue
            invisible = session.quest_flags.get("buff:invisible_turns")
            distance = abs(monster.x - session.party.x) + abs(monster.y - session.party.y)
            if isinstance(invisible, int) and invisible > 0 and distance > 2:
                continue
            if self._monster_confuse_turns(session, monster.entity_id) > 0:
                options = [(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)]
                step_x, step_y = random.choice(options)
                nx, ny = monster.x + step_x, monster.y + step_y
                if self._monster_can_enter_tile(session, monster, nx, ny):
                    monster.x, monster.y = nx, ny
                continue
            if self._monster_fear_turns(session, monster.entity_id) > 0:
                if distance < 8:
                    step_x = -1 if session.party.x > monster.x else 1 if session.party.x < monster.x else 0
                    step_y = -1 if session.party.y > monster.y else 1 if session.party.y < monster.y else 0
                    nx, ny = monster.x + step_x, monster.y + step_y
                    if self._monster_can_enter_tile(session, monster, nx, ny):
                        monster.x, monster.y = nx, ny
                        monster.facing = self._facing_from_delta(step_x, step_y, monster.facing)
                        self._apply_tile_field_entry(session, nx, ny, monster, monster.name)
                continue
            if distance < 6:
                step_x = 1 if session.party.x > monster.x else -1 if session.party.x < monster.x else 0
                step_y = 1 if session.party.y > monster.y else -1 if session.party.y < monster.y else 0
                nx, ny = monster.x + step_x, monster.y + step_y
                if self._monster_can_enter_tile(session, monster, nx, ny):
                    monster.x, monster.y = nx, ny
                    monster.facing = self._facing_from_delta(step_x, step_y, monster.facing)
                    self._apply_tile_field_entry(session, nx, ny, monster, monster.name)

    def _sleep_flag_key(self, entity_id: str) -> str:
        return f"sleep:{entity_id}"

    def _monster_sleep_turns(self, session: GameSession, entity_id: str) -> int:
        turns = session.quest_flags.get(self._sleep_flag_key(entity_id))
        if isinstance(turns, int) and not isinstance(turns, bool) and turns > 0:
            return turns
        return 0

    def _set_monster_sleep(self, session: GameSession, entity_id: str, turns: int) -> None:
        current = self._monster_sleep_turns(session, entity_id)
        session.quest_flags[self._sleep_flag_key(entity_id)] = max(current, turns)

    def _clear_monster_sleep(self, session: GameSession, entity_id: str) -> None:
        session.quest_flags.pop(self._sleep_flag_key(entity_id), None)

    def _fear_flag_key(self, entity_id: str) -> str:
        return f"fear:{entity_id}"

    def _charm_flag_key(self, entity_id: str) -> str:
        return f"charm:{entity_id}"

    def _monster_fear_turns(self, session: GameSession, entity_id: str) -> int:
        turns = session.quest_flags.get(self._fear_flag_key(entity_id))
        if isinstance(turns, int) and not isinstance(turns, bool) and turns > 0:
            return turns
        return 0

    def _monster_charm_turns(self, session: GameSession, entity_id: str) -> int:
        turns = session.quest_flags.get(self._charm_flag_key(entity_id))
        if isinstance(turns, int) and not isinstance(turns, bool) and turns > 0:
            return turns
        return 0

    def _set_monster_fear(self, session: GameSession, entity_id: str, turns: int) -> None:
        current = self._monster_fear_turns(session, entity_id)
        session.quest_flags[self._fear_flag_key(entity_id)] = max(current, turns)

    def _set_monster_charm(self, session: GameSession, entity_id: str, turns: int) -> None:
        current = self._monster_charm_turns(session, entity_id)
        session.quest_flags[self._charm_flag_key(entity_id)] = max(current, turns)

    def _is_undead_monster(self, monster: Entity) -> bool:
        token = f"{monster.entity_id} {monster.name}".lower()
        undead_terms = (
            "skeleton",
            "lich",
            "ghast",
            "zombie",
            "ghost",
            "wraith",
            "ghoul",
            "undead",
            "vampire",
        )
        return any(term in token for term in undead_terms)

    def _magic_contest(self, session: GameSession, monster: Entity, power: int, bonus: int = 0) -> bool:
        attack_roll = random.randint(1, 6) + power + bonus
        defense_roll = random.randint(1, 6) + monster.defense + 2
        return attack_roll >= defense_roll

    def _is_blink_target_tile(self, session: GameSession, x: int, y: int) -> bool:
        if not session.place.in_bounds(x, y):
            return False
        if not self._party_can_enter_tile(session, x, y):
            return False
        if session.place.monster_at(x, y) is not None:
            return False
        return True

    def _relocate_party(self, session: GameSession, x: int, y: int) -> None:
        session.party.x, session.party.y = x, y
        for member in session.party.members:
            member.x, member.y = x, y

    def _cast_sleep_targeted(self, session: GameSession, spell, monster: Entity) -> None:
        self._consume_reagents(session, spell.spell_id)
        sleep_turns = max(3, min(12, spell.circle * 2 + 1))
        self._set_monster_sleep(session, monster.entity_id, sleep_turns)
        session.append_log(f"You cast {spell.name}. {monster.name} falls asleep ({sleep_turns} turns).")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell.name}", (200, 200, 255), world_pos=(monster.x, monster.y)
        )
        session.advance_turn()

    def _cast_sleep_area(self, session: GameSession, spell_name: str, circle: int) -> None:
        radius = max(2, min(8, circle))
        affected = 0
        sleep_turns = max(4, min(14, circle * 2))
        for monster in session.place.monsters:
            if not monster.is_alive():
                continue
            if self._distance_from_party(session, monster.x, monster.y) <= radius:
                self._set_monster_sleep(session, monster.entity_id, sleep_turns)
                affected += 1
        if affected:
            session.append_log(
                f"You cast {spell_name}. {affected} creature(s) fall asleep ({sleep_turns} turns)."
            )
        else:
            session.append_log(f"You cast {spell_name}. No creatures are close enough to affect.")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name}", (200, 200, 255), world_pos=(session.party.x, session.party.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None and self._monster_sleep_turns(session, adjacent.entity_id) <= 0:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_charm_targeted(self, session: GameSession, spell, monster: Entity) -> None:
        self._consume_reagents(session, spell.spell_id)
        if self._magic_contest(session, monster, spell.circle, bonus=1):
            charm_turns = max(5, min(12, spell.circle + 2))
            self._set_monster_charm(session, monster.entity_id, charm_turns)
            session.append_log(f"You cast {spell.name}. {monster.name} is charmed ({charm_turns} turns).")
        else:
            session.append_log(f"You cast {spell.name}. {monster.name} resists charm.")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell.name}", (255, 180, 220), world_pos=(monster.x, monster.y)
        )
        adjacent = self._adjacent_monster(session)
        if (
            adjacent is not None
            and adjacent.entity_id == monster.entity_id
            and self._monster_charm_turns(session, monster.entity_id) <= 0
        ):
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_fear(self, session: GameSession, spell_name: str, circle: int) -> None:
        fear_turns = max(4, min(12, circle + 2))
        affected = 0
        for monster in session.place.monsters:
            if not monster.is_alive() or not monster.hostile:
                continue
            if self._magic_contest(session, monster, circle, bonus=8):
                self._set_monster_fear(session, monster.entity_id, fear_turns)
                session.append_log(f"{monster.name} flees in terror!")
                affected += 1
            else:
                session.append_log(f"{monster.name} resists your fear.")
        if affected:
            session.append_log(f"You cast {spell_name}. {affected} foe(s) flee ({fear_turns} turns).")
        else:
            session.append_log(f"You cast {spell_name}, but no foe succumbs to fear.")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name}", (210, 190, 255), world_pos=(session.party.x, session.party.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None and self._monster_fear_turns(session, adjacent.entity_id) <= 0:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_turn_undead(self, session: GameSession, spell_name: str, circle: int) -> None:
        fear_turns = max(5, min(14, circle * 2 + 1))
        affected = 0
        for monster in session.place.monsters:
            if not monster.is_alive() or not monster.hostile:
                continue
            if not self._is_undead_monster(monster):
                continue
            if self._magic_contest(session, monster, circle, bonus=3):
                self._set_monster_fear(session, monster.entity_id, fear_turns)
                session.append_log(f"{monster.name} is turned!")
                affected += 1
            else:
                session.append_log(f"{monster.name} resists turn undead.")
        if affected:
            session.append_log(f"You cast {spell_name}. {affected} undead flee ({fear_turns} turns).")
        else:
            session.append_log(f"You cast {spell_name}. No undead are repelled.")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name}", (220, 235, 255), world_pos=(session.party.x, session.party.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None and self._monster_fear_turns(session, adjacent.entity_id) <= 0:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_blink_spell(self, session: GameSession, spell, x: int, y: int) -> None:
        self._consume_reagents(session, spell.spell_id)
        old_x, old_y = session.party.x, session.party.y
        self._relocate_party(session, x, y)
        lead = session.party.lead()
        self._apply_tile_field_entry(session, x, y, lead, "You")
        if spell.effect_kind == "gate":
            label = "gate travel"
        elif spell.effect_kind == "teleport":
            label = "teleport"
        else:
            label = "blink"
        session.append_log(f"You cast {spell.name} and {label} to ({x}, {y}).")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell.name}", (180, 220, 255), world_pos=(x, y)
        )
        session.advance_turn()
        session.party.food = max(0, session.party.food - 1)
        if (old_x, old_y) != (x, y):
            self._check_auto_combat(session)
            self._npc_turn(session)

    def _finish_spell_cast(
        self,
        session: GameSession,
        spell_name: str,
        color: tuple[int, int, int],
        *,
        counterattack: bool = True,
    ) -> None:
        self._clear_combat_feedback(session)
        self._set_feedback(session, f"You: {spell_name}", color, world_pos=(session.party.x, session.party.y))
        if counterattack:
            adjacent = self._adjacent_monster(session)
            if adjacent is not None:
                self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _monster_ensnare_turns(self, session: GameSession, entity_id: str) -> int:
        turns = session.quest_flags.get(f"ensnare:{entity_id}")
        if isinstance(turns, int) and not isinstance(turns, bool) and turns > 0:
            return turns
        return 0

    def _monster_confuse_turns(self, session: GameSession, entity_id: str) -> int:
        turns = session.quest_flags.get(f"confuse:{entity_id}")
        if isinstance(turns, int) and not isinstance(turns, bool) and turns > 0:
            return turns
        return 0

    def _set_monster_ensnare(self, session: GameSession, entity_id: str, turns: int) -> None:
        key = f"ensnare:{entity_id}"
        current = self._monster_ensnare_turns(session, entity_id)
        session.quest_flags[key] = max(current, turns)

    def _set_monster_confuse(self, session: GameSession, entity_id: str, turns: int) -> None:
        key = f"confuse:{entity_id}"
        current = self._monster_confuse_turns(session, entity_id)
        session.quest_flags[key] = max(current, turns)

    def _is_spider_monster(self, monster: Entity) -> bool:
        token = f"{monster.entity_id} {monster.name}".lower()
        return "spider" in token

    def _traps_in_radius(self, session: GameSession, radius: int) -> list[tuple[Trap, int]]:
        found: list[tuple[Trap, int]] = []
        for trap in session.place.traps:
            if trap.disarmed:
                continue
            distance = self._distance_from_party(session, trap.x, trap.y)
            if distance <= radius:
                found.append((trap, distance))
        found.sort(key=lambda pair: pair[1])
        return found

    def _cone_tiles_from_facing(
        self, session: GameSession, x: int, y: int, facing: str, depth: int
    ) -> list[tuple[int, int]]:
        vectors = {
            "n": ((0, -1), (1, 0)),
            "s": ((0, 1), (-1, 0)),
            "e": ((1, 0), (0, -1)),
            "w": ((-1, 0), (0, 1)),
        }
        forward, perpendicular = vectors.get(facing, vectors["s"])
        tiles: list[tuple[int, int]] = []
        for distance in range(1, depth + 1):
            cx = x + forward[0] * distance
            cy = y + forward[1] * distance
            tiles.append((cx, cy))
            for side in (-1, 1):
                tiles.append((cx + perpendicular[0] * side, cy + perpendicular[1] * side))
        return [
            (tx, ty)
            for tx, ty in tiles
            if session.place.in_bounds(tx, ty) and (tx, ty) != (x, y)
        ]

    def _adjacent_passable_tile(
        self, session: GameSession, x: int, y: int
    ) -> tuple[int, int] | None:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self._party_can_enter_tile(session, nx, ny) and session.place.monster_at(nx, ny) is None:
                return nx, ny
        return None

    def _is_telekinesis_target(self, session: GameSession, x: int, y: int) -> bool:
        if session.place.ground_items.get((x, y)):
            return True
        if session.place.chest_at(x, y) is not None:
            return True
        if session.place.monster_at(x, y) is not None:
            return True
        return False

    def _cast_trap_detect(self, session: GameSession, spell_name: str, circle: int) -> None:
        radius = max(4, min(12, circle * 2 + 2))
        traps = self._traps_in_radius(session, radius)
        for trap, _ in traps:
            trap.detected = True
        if traps:
            nearest, distance = traps[0]
            session.append_log(
                f"You cast {spell_name}. Detected {len(traps)} trap(s) (nearest {distance} tiles)."
            )
        else:
            session.append_log(f"You cast {spell_name}. No traps sensed nearby.")
        self._finish_spell_cast(session, spell_name, (210, 225, 255))

    def _cast_trap_disarm(self, session: GameSession, spell_name: str, circle: int) -> None:
        radius = max(2, min(6, circle + 1))
        disarmed = 0
        for trap, distance in self._traps_in_radius(session, radius):
            if distance > 1:
                continue
            trap.detected = True
            trap.disarmed = True
            disarmed += 1
        if disarmed:
            session.append_log(f"You cast {spell_name}. Disarmed {disarmed} trap(s).")
        else:
            session.append_log(f"You cast {spell_name}. No adjacent traps to disarm.")
        self._finish_spell_cast(session, spell_name, (220, 230, 255))

    def _cast_smoke(self, session: GameSession, spell_name: str, circle: int) -> None:
        turns = max(4, min(10, circle + 3))
        placed = self._place_field_tiles(session, session.party.x, session.party.y, "smoke", turns)
        session.append_log(f"You cast {spell_name}. Smoke spreads across {placed} tile(s).")
        self._finish_spell_cast(session, spell_name, (190, 190, 200))

    def _cast_summon(self, session: GameSession, spell) -> None:
        profiles = {
            "in_bet_xen": ("summon_rat", "Summoned Rat", "s_rat", 5, 5, 2, 1),
            "kal_xen": ("summon_beast", "Summoned Beast", "s_wolf", 8, 8, 3, 2),
            "kal_xen_corp": ("summon_skeleton", "Summoned Skeleton", "s_skeleton", 7, 7, 2, 1),
            "kal_xen_nox": ("summon_slime", "Summoned Slime", "s_slime", 6, 6, 2, 1),
        }
        profile = profiles.get(spell.spell_id)
        if profile is None:
            session.append_log(f"You cast {spell.name}, but nothing answers.")
            self._finish_spell_cast(session, spell.name, (200, 220, 255))
            return
        entity_id, name, sprite, hp, max_hp, attack, defense = profile
        spawn = self._adjacent_passable_tile(session, session.party.x, session.party.y)
        if spawn is None:
            session.append_log(f"You cast {spell.name}, but there is no room to summon.")
            self._finish_spell_cast(session, spell.name, (200, 220, 255))
            return
        sx, sy = spawn
        if any(monster.entity_id == entity_id for monster in session.place.monsters):
            entity_id = f"{entity_id}_{session.party.turn_count}"
        ally = Entity(
            entity_id=entity_id,
            name=name,
            x=sx,
            y=sy,
            sprite_key=sprite,
            hostile=False,
            hp=hp,
            max_hp=max_hp,
            attack=attack,
            defense=defense,
        )
        session.place.monsters.append(ally)
        duration = max(6, min(16, spell.circle * 2 + 2))
        session.quest_flags[f"summon:{entity_id}"] = duration
        session.append_log(f"You cast {spell.name}. {name} appears ({duration} turns).")
        self._finish_spell_cast(session, spell.name, (210, 235, 255))

    def _cast_calm_spiders(self, session: GameSession, spell_name: str, circle: int) -> None:
        calm_turns = max(5, min(12, circle * 2 + 1))
        affected = 0
        for monster in session.place.monsters:
            if not monster.is_alive() or not self._is_spider_monster(monster):
                continue
            self._set_monster_charm(session, monster.entity_id, calm_turns)
            affected += 1
        if affected:
            session.append_log(f"You cast {spell_name}. {affected} spider(s) calm down.")
        else:
            session.append_log(f"You cast {spell_name}. No spiders are nearby.")
        self._finish_spell_cast(session, spell_name, (220, 210, 255))

    def _cast_force_field(self, session: GameSession, spell_name: str, circle: int) -> None:
        turns = max(5, min(14, circle + 4))
        placed = self._place_field_tiles(session, session.party.x, session.party.y, "energy", turns)
        added = max(2, min(6, circle // 2 + 2))
        session.party.ward_charges = min(12, session.party.ward_charges + added)
        session.append_log(
            f"You cast {spell_name}. Energy fields cover {placed} tile(s); ward +{added}."
        )
        self._finish_spell_cast(session, spell_name, (180, 210, 255))

    def _cast_invisibility(self, session: GameSession, spell_name: str, circle: int) -> None:
        duration = max(6, min(18, circle * 2 + 2))
        session.quest_flags["buff:invisible_turns"] = duration + 1
        session.append_log(f"You cast {spell_name}. You fade from sight ({duration} turns).")
        self._finish_spell_cast(session, spell_name, (200, 200, 240))

    def _cast_confusion(self, session: GameSession, spell_name: str, circle: int) -> None:
        radius = max(3, min(10, circle + 2))
        confuse_turns = max(4, min(12, circle + 2))
        affected = 0
        for monster, distance in self._hostiles_in_radius(session, radius):
            if self._magic_contest(session, monster, circle):
                self._set_monster_confuse(session, monster.entity_id, confuse_turns)
                affected += 1
        if affected:
            session.append_log(f"You cast {spell_name}. {affected} foe(s) are confused.")
        else:
            session.append_log(f"You cast {spell_name}. No foe is confused.")
        self._finish_spell_cast(session, spell_name, (230, 210, 255))

    def _cast_wind(self, session: GameSession, spell_name: str) -> None:
        directions = ("north", "east", "south", "west")
        direction = random.choice(directions)
        session.quest_flags["world:wind_direction"] = direction
        session.append_log(f"You cast {spell_name}. The wind shifts to the {direction}.")
        self._finish_spell_cast(session, spell_name, (210, 230, 255))

    def _cast_resurrection(self, session: GameSession, spell_name: str, circle: int) -> None:
        lead = session.party.lead()
        if lead.hp <= 0:
            lead.hp = lead.max_hp
            session.append_log(f"You cast {spell_name}. The Wanderer is restored to life.")
        else:
            heal = random.randint(8, 12 + circle * 2)
            lead.hp = min(lead.max_hp, lead.hp + heal)
            session.append_log(f"You cast {spell_name} and restore {heal} HP.")
        self._finish_spell_cast(session, spell_name, (190, 255, 210))

    def _cast_time_stop(self, session: GameSession, spell_name: str, circle: int) -> None:
        stop_turns = max(5, min(14, circle + 3))
        affected = 0
        for monster in session.place.monsters:
            if not monster.is_alive() or not monster.hostile:
                continue
            self._set_monster_sleep(session, monster.entity_id, stop_turns)
            affected += 1
        session.append_log(f"You cast {spell_name}. Time freezes for {affected} hostile creature(s).")
        self._finish_spell_cast(session, spell_name, (220, 220, 255))

    def _cast_raise_ship(self, session: GameSession, spell_name: str) -> None:
        session.quest_flags["quest:ship_raiseable"] = True
        self.quest_engine.on_quest_flag(session, "quest:ship_raiseable")
        session.append_log(
            f"You cast {spell_name}. Distant waters stir—perhaps a sunken hull can be raised."
        )
        self._finish_spell_cast(session, spell_name, (200, 230, 255))

    def _cast_tremor(self, session: GameSession, spell_name: str, circle: int) -> None:
        radius = max(4, min(10, circle + 2))
        sleep_turns = max(3, min(8, circle))
        damaged = 0
        for monster, _ in self._hostiles_in_radius(session, radius):
            damage = random.randint(2, 4 + circle)
            monster.hp = max(0, monster.hp - damage)
            damaged += 1
            self._set_monster_sleep(session, monster.entity_id, sleep_turns)
            if not monster.is_alive():
                session.quest_flags[f"defeated:{monster.entity_id}"] = True
        session.victory = all(not monster.is_alive() for monster in session.place.monsters)
        session.append_log(
            f"You cast {spell_name}. The ground shakes; {damaged} foe(s) are struck and knocked down."
        )
        self._finish_spell_cast(session, spell_name, (255, 200, 150))

    def _cast_cone_spell(self, session: GameSession, spell, cone_kind: str) -> None:
        facing = session.party.lead().facing
        depth = max(3, min(7, spell.circle + 2))
        tiles = self._cone_tiles_from_facing(session, session.party.x, session.party.y, facing, depth)
        hit = 0
        for monster in session.place.monsters:
            if not monster.is_alive() or (monster.x, monster.y) not in tiles:
                continue
            hit += 1
            if cone_kind == "fire":
                damage = random.randint(2, 4 + spell.circle)
                monster.hp = max(0, monster.hp - damage)
                session.append_log(f"{spell.name} burns {monster.name} for {damage}.")
            elif cone_kind == "poison":
                damage = random.randint(1, 3 + spell.circle)
                monster.hp = max(0, monster.hp - damage)
                self._set_monster_poison(session, monster.entity_id, max(3, spell.circle))
                session.append_log(f"{spell.name} poisons {monster.name} for {damage}.")
            else:
                self._set_monster_sleep(session, monster.entity_id, max(3, spell.circle + 1))
                session.append_log(f"{spell.name} lulls {monster.name} toward sleep.")
            if not monster.is_alive():
                session.quest_flags[f"defeated:{monster.entity_id}"] = True
        session.victory = all(not monster.is_alive() for monster in session.place.monsters)
        if not hit:
            session.append_log(f"You cast {spell.name}, but the wind finds no foes.")
        else:
            session.append_log(f"You cast {spell.name}. The wind affects {hit} creature(s).")
        self._finish_spell_cast(session, spell.name, (255, 205, 170))

    def _cast_web_targeted(self, session: GameSession, spell, monster: Entity) -> None:
        self._consume_reagents(session, spell.spell_id)
        ensnare_turns = max(4, min(10, spell.circle + 2))
        if self._magic_contest(session, monster, spell.circle):
            self._set_monster_ensnare(session, monster.entity_id, ensnare_turns)
            session.append_log(f"You cast {spell.name}. {monster.name} is ensnared ({ensnare_turns} turns).")
        else:
            session.append_log(f"You cast {spell.name}. {monster.name} breaks free of the web.")
        self._clear_combat_feedback(session)
        self._set_feedback(session, f"You: {spell.name}", (210, 230, 200), world_pos=(monster.x, monster.y))
        if self._distance_from_party(session, monster.x, monster.y) <= 1:
            self._enemy_counterattack(session, monster)
        session.advance_turn()

    def _cast_illusion_targeted(self, session: GameSession, spell, monster: Entity) -> None:
        self._consume_reagents(session, spell.spell_id)
        if self._magic_contest(session, monster, spell.circle):
            charm_turns = max(4, min(10, spell.circle + 1))
            self._set_monster_charm(session, monster.entity_id, charm_turns)
            session.append_log(f"You cast {spell.name}. {monster.name} is fooled by the illusion.")
        else:
            session.append_log(f"You cast {spell.name}. {monster.name} sees through the illusion.")
        self._clear_combat_feedback(session)
        self._set_feedback(session, f"You: {spell.name}", (230, 210, 255), world_pos=(monster.x, monster.y))
        if (
            self._distance_from_party(session, monster.x, monster.y) <= 1
            and self._monster_charm_turns(session, monster.entity_id) <= 0
        ):
            self._enemy_counterattack(session, monster)
        session.advance_turn()

    def _cast_clone_targeted(self, session: GameSession, spell, monster: Entity) -> None:
        self._consume_reagents(session, spell.spell_id)
        spawn = self._adjacent_passable_tile(session, monster.x, monster.y)
        if spawn is None:
            session.append_log(f"You cast {spell.name}, but there is no space for a clone.")
            self._finish_spell_cast(session, spell.name, (220, 220, 255), counterattack=False)
            return
        sx, sy = spawn
        clone_id = f"clone_{monster.entity_id}_{session.party.turn_count}"
        clone = Entity(
            entity_id=clone_id,
            name=f"Clone of {monster.name}",
            x=sx,
            y=sy,
            sprite_key=monster.sprite_key,
            hostile=monster.hostile,
            hp=max(1, monster.hp // 2),
            max_hp=max(1, monster.max_hp // 2),
            attack=monster.attack,
            defense=monster.defense,
        )
        session.place.monsters.append(clone)
        duration = max(5, min(12, spell.circle + 2))
        session.quest_flags[f"summon:{clone_id}"] = duration
        session.append_log(f"You cast {spell.name}. A clone of {monster.name} appears.")
        self._clear_combat_feedback(session)
        self._set_feedback(session, f"You: {spell.name}", (220, 230, 255), world_pos=(sx, sy))
        if self._distance_from_party(session, monster.x, monster.y) <= 1:
            self._enemy_counterattack(session, monster)
        session.advance_turn()

    def _cast_telekinesis(self, session: GameSession, spell, x: int, y: int) -> None:
        self._consume_reagents(session, spell.spell_id)
        items = session.place.ground_items.pop((x, y), None)
        if items:
            session.party.inventory.extend(items)
            session.append_log(f"You cast {spell.name} and draw {len(items)} item(s) to hand.")
        else:
            chest = session.place.chest_at(x, y)
            monster = session.place.monster_at(x, y)
            if chest is not None and not chest.opened:
                chest.opened = True
                if chest.items:
                    session.place.ground_items[(chest.x, chest.y)] = list(chest.items)
                session.quest_flags[f"opened:{chest.chest_id}"] = True
                session.append_log(f"You cast {spell.name} and wrench the chest open.")
            elif monster is not None and monster.is_alive():
                step_x = 1 if session.party.x > monster.x else -1 if session.party.x < monster.x else 0
                step_y = 1 if session.party.y > monster.y else -1 if session.party.y < monster.y else 0
                nx, ny = monster.x + step_x, monster.y + step_y
                if self._monster_can_enter_tile(session, monster, nx, ny):
                    monster.x, monster.y = nx, ny
                    session.append_log(f"You cast {spell.name} and drag {monster.name} closer.")
                else:
                    session.append_log(f"You cast {spell.name}, but {monster.name} holds firm.")
            else:
                session.append_log(f"You cast {spell.name}, but nothing moves.")
        self._finish_spell_cast(session, spell.name, (200, 220, 255))

    def _party_poison_turns(self, session: GameSession) -> int:
        turns = session.quest_flags.get("buff:poison_turns")
        if isinstance(turns, int) and not isinstance(turns, bool) and turns > 0:
            return turns
        return 0

    def _set_party_poison(self, session: GameSession, turns: int) -> None:
        current = self._party_poison_turns(session)
        session.quest_flags["buff:poison_turns"] = max(current, turns)

    def _monster_poison_turns(self, session: GameSession, entity_id: str) -> int:
        turns = session.quest_flags.get(f"poison:{entity_id}")
        if isinstance(turns, int) and not isinstance(turns, bool) and turns > 0:
            return turns
        return 0

    def _set_monster_poison(self, session: GameSession, entity_id: str, turns: int) -> None:
        current = self._monster_poison_turns(session, entity_id)
        session.quest_flags[f"poison:{entity_id}"] = max(current, turns)

    def _cast_poison_targeted(self, session: GameSession, spell, monster: Entity) -> None:
        self._consume_reagents(session, spell.spell_id)
        damage = random.randint(2 + spell.circle, 4 + spell.circle)
        monster.hp = max(0, monster.hp - damage)
        poison_turns = max(3, min(10, spell.circle * 2 + 1))
        session.append_log(
            f"You cast {spell.name} on {monster.name} for {damage} damage and poison ({poison_turns} turns)."
        )
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell.name} {damage}", (150, 220, 140), world_pos=(monster.x, monster.y)
        )
        if not monster.is_alive():
            session.append_log(f"{monster.name} is defeated.")
            session.quest_flags[f"defeated:{monster.entity_id}"] = True
            session.victory = True
            session.advance_turn()
            return
        if self._distance_from_party(session, monster.x, monster.y) <= 1:
            if self._monster_sleep_turns(session, monster.entity_id) <= 0:
                self._enemy_counterattack(session, monster)
        session.advance_turn()
        if monster.is_alive():
            self._set_monster_poison(session, monster.entity_id, poison_turns)

    def _cast_cure_poison(
        self, session: GameSession, spell_name: str, spell_id: str, circle: int
    ) -> None:
        cured_party = False
        if self._party_poison_turns(session) > 0:
            session.quest_flags.pop("buff:poison_turns", None)
            cured_party = True
        cured_monsters = 0
        for monster in session.place.monsters:
            if self._monster_poison_turns(session, monster.entity_id) > 0:
                session.quest_flags.pop(f"poison:{monster.entity_id}", None)
                cured_monsters += 1
        if spell_id == "vas_an_nox":
            heal = random.randint(4, 8 + circle)
            lead = session.party.lead()
            lead.hp = min(lead.max_hp, lead.hp + heal)
            session.append_log(f"{spell_name} restores {heal} HP.")
        if cured_party or cured_monsters:
            parts: list[str] = []
            if cured_party:
                parts.append("your poison")
            if cured_monsters:
                parts.append(f"{cured_monsters} poisoned foe(s)")
            session.append_log(f"You cast {spell_name}. Cured {', '.join(parts)}.")
        else:
            session.append_log(f"You cast {spell_name}. No poison afflictions to cure.")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name}", (170, 230, 180), world_pos=(session.party.x, session.party.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None and self._monster_sleep_turns(session, adjacent.entity_id) <= 0:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _cast_awaken(self, session: GameSession, spell_name: str, circle: int) -> None:
        radius = max(3, min(10, circle + 2))
        awakened = 0
        for monster in session.place.monsters:
            if self._monster_sleep_turns(session, monster.entity_id) <= 0:
                continue
            if self._distance_from_party(session, monster.x, monster.y) <= radius:
                self._clear_monster_sleep(session, monster.entity_id)
                awakened += 1
                session.append_log(f"{monster.name} awakens.")
        if awakened:
            session.append_log(f"You cast {spell_name}. {awakened} sleeping creature(s) awaken.")
        else:
            session.append_log(f"You cast {spell_name}. Nothing nearby is asleep.")
        self._clear_combat_feedback(session)
        self._set_feedback(
            session, f"You: {spell_name}", (210, 230, 255), world_pos=(session.party.x, session.party.y)
        )
        adjacent = self._adjacent_monster(session)
        if adjacent is not None:
            self._enemy_counterattack(session, adjacent)
        session.advance_turn()

    def _field_kind_for_spell(self, spell_id: str, spell_name: str) -> str:
        token = f"{spell_id} {spell_name}".lower()
        if "poison field" in token:
            return "poison"
        if "sleep field" in token:
            return "sleep"
        return "fire"

    def _place_field_tiles(
        self, session: GameSession, center_x: int, center_y: int, field_kind: str, turns: int
    ) -> int:
        placed = 0
        for x, y in self._tiles_in_range(center_x, center_y, 1):
            if not session.place.in_bounds(x, y):
                continue
            if not session.place.terrain_at(x, y).passable:
                continue
            session.place.tile_fields[(x, y)] = TileField(
                x=x, y=y, field_kind=field_kind, turns_remaining=turns
            )
            placed += 1
        return placed

    def _clear_tile_fields_in_radius(
        self, session: GameSession, center_x: int, center_y: int, radius: int
    ) -> int:
        to_clear = [
            pos
            for pos in session.place.tile_fields
            if abs(pos[0] - center_x) + abs(pos[1] - center_y) <= radius
        ]
        for pos in to_clear:
            session.place.tile_fields.pop(pos, None)
        return len(to_clear)

    def _apply_tile_field_entry(
        self, session: GameSession, x: int, y: int, entity: Entity, label: str
    ) -> None:
        tile_field = session.place.field_at(x, y)
        if tile_field is None or not entity.is_alive():
            return
        if tile_field.field_kind in {"sleep", "smoke"}:
            session.append_log(f"{label} stumbles in a {tile_field.field_kind} field.")
            return
        if tile_field.field_kind == "energy":
            session.append_log(f"{label} is repelled by an energy field.")
            return
        if tile_field.field_kind == "poison":
            damage = random.randint(1, 3)
            verb = "is poisoned by"
            if entity.entity_id == session.party.lead().entity_id:
                self._set_party_poison(session, max(4, tile_field.turns_remaining))
            else:
                self._set_monster_poison(session, entity.entity_id, max(4, tile_field.turns_remaining))
        else:
            damage = random.randint(2, 4)
            verb = "is burned by"
        entity.hp = max(0, entity.hp - damage)
        session.append_log(f"{label} {verb} a {tile_field.field_kind} field for {damage}.")
        if not entity.is_alive() and entity.entity_id != session.party.lead().entity_id:
            session.append_log(f"{entity.name} is defeated.")
            session.quest_flags[f"defeated:{entity.entity_id}"] = True
            session.victory = all(not monster.is_alive() for monster in session.place.monsters)

    def _party_can_enter_tile(self, session: GameSession, x: int, y: int) -> bool:
        if not session.place.passable(x, y):
            return False
        if session.place.npc_at(x, y) is not None:
            return False
        chest = session.place.chest_at(x, y)
        if chest is not None and not chest.opened:
            return False
        return True

    def _monster_can_enter_tile(self, session: GameSession, monster: Entity, x: int, y: int) -> bool:
        if not session.place.in_bounds(x, y):
            return False
        terrain = session.place.terrain_at(x, y)
        if not terrain.passable:
            return False
        if (x, y) == (session.party.x, session.party.y):
            return False
        if session.place.npc_at(x, y) is not None:
            return False
        chest = session.place.chest_at(x, y)
        if chest is not None and not chest.opened:
            return False
        for other in session.place.monsters:
            if other is monster or not other.is_alive():
                continue
            if (other.x, other.y) == (x, y):
                return False
        return True

    def _facing_from_delta(self, dx: int, dy: int, current: str = "s") -> str:
        if dx > 0:
            return "e"
        if dx < 0:
            return "w"
        if dy > 0:
            return "s"
        if dy < 0:
            return "n"
        return current

    def _cast_spell_id(self, action: str | None) -> str | None:
        if not isinstance(action, str):
            return None
        if not action.startswith("cast_"):
            return None
        return action.replace("cast_", "", 1)

    def _has_reagents_for_spell(self, session: GameSession, spell_id: str) -> bool:
        spell = get_spell(spell_id)
        if spell is None:
            return False
        for reagent, qty in spell.reagents.items():
            if session.party.reagents.get(reagent, 0) < qty:
                return False
        return True

    def _consume_reagents(self, session: GameSession, spell_id: str) -> None:
        spell = get_spell(spell_id)
        if spell is None:
            return
        for reagent, qty in spell.reagents.items():
            available = int(session.party.reagents.get(reagent, 0))
            session.party.reagents[reagent] = max(0, available - qty)
