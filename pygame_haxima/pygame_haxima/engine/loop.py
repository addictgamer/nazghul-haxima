from __future__ import annotations

import random

from pygame_haxima.data.save_manager import SaveManager
from pygame_haxima.domain.models import Entity, GameSession, Mode
from pygame_haxima.engine.audio import AudioManager
from pygame_haxima.engine.events import EngineEvent, EngineEventType
from pygame_haxima.engine.renderer import Renderer


class TurnLoop:
    def __init__(self, renderer: Renderer, audio: AudioManager, save_manager: SaveManager) -> None:
        self.renderer = renderer
        self.audio = audio
        self.save_manager = save_manager

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
            if event.kind == EngineEventType.MOUSE_TILE:
                if session.show_save_load_menu:
                    continue
                self._handle_mouse_move(session, event.payload["tile"])
                continue
            if event.kind != EngineEventType.ACTION:
                continue
            action = event.payload["action"]
            if session.show_save_load_menu:
                self._handle_save_load_menu_action(session, action)
                continue
            if action == "options_menu":
                self._toggle_options_menu(session)
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
            elif action == "examine":
                self._start_targeting(session, "examine", "Xamine-<target>(Enter confirm, Esc cancel)")
            elif action == "save":
                self._open_save_load_menu(session, "save")
            elif action == "load":
                self._open_save_load_menu(session, "load")
            elif action == "help":
                self._help(session)
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
        nx, ny = session.party.x + dx, session.party.y + dy
        if not self._party_can_enter_tile(session, nx, ny):
            session.append_log("Blocked.")
            return
        session.party.x, session.party.y = nx, ny
        session.party.members[0].x, session.party.members[0].y = nx, ny
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
        session.mode = Mode.COMBAT
        session.combat.active = True
        session.combat.enemy_ids = [monster.entity_id]
        session.combat.message = f"Engaged {monster.name}"
        self._resolve_combat_round(session, monster)
        if not monster.is_alive():
            session.append_log(f"{monster.name} falls.")
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
        session.append_log("Move: arrows/WASD | t talk | o open | g get | f attack | x examine")
        session.append_log(
            "F5 save | F9 load | F10 options | F11 fullscreen | F2 terrain IDs | F3 sprite warnings | F4 runtime state"
        )
        session.append_log("Target mode: arrows move cursor | Enter confirm | Esc cancel")

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
        if action == "examine":
            self._examine(session, x, y)
            self._end_targeting(session)

    def _distance_from_party(self, session: GameSession, x: int, y: int) -> int:
        return abs(session.party.x - x) + abs(session.party.y - y)

    def _is_tile_in_target_range(self, session: GameSession, x: int, y: int) -> bool:
        if session.targeting_action in {"talk", "open", "attack"}:
            return self._distance_from_party(session, x, y) <= 1
        return True

    def _has_action_target_in_range(self, session: GameSession, action: str) -> bool:
        px, py = session.party.x, session.party.y
        candidates = ((px, py), (px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1))
        if action == "talk":
            return any(session.place.npc_at(x, y) is not None for x, y in candidates)
        if action == "open":
            return any(session.place.chest_at(x, y) is not None for x, y in candidates)
        if action == "attack":
            return any(session.place.monster_at(x, y) is not None for x, y in candidates)
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
        return px, py

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

    def _resolve_combat_round(self, session: GameSession, monster: Entity) -> None:
        attacker = session.party.lead()
        attack_roll = random.randint(1, 6) + attacker.attack
        defense_roll = random.randint(1, 6) + monster.defense
        if attack_roll <= defense_roll:
            session.append_log(f"You miss the {monster.name}.")
            self._set_feedback(session, "Miss", (230, 220, 120), world_pos=(monster.x, monster.y))
            return
        damage = max(1, attack_roll - defense_roll)
        monster.hp = max(0, monster.hp - damage)
        session.append_log(f"You hit {monster.name} for {damage} damage.")
        self._set_feedback(
            session, f"Hit {damage}", (255, 170, 140), world_pos=(monster.x, monster.y)
        )
        self.audio.play_effect("sounds/hit.wav")

    def _enemy_counterattack(self, session: GameSession, monster: Entity) -> None:
        if not monster.is_alive():
            return
        target = session.party.lead()
        attack_roll = random.randint(1, 6) + monster.attack
        defense_roll = random.randint(1, 6) + target.defense
        if attack_roll <= defense_roll:
            session.append_log(f"{monster.name} misses.")
            self._set_feedback(
                session, f"{monster.name} misses", (220, 210, 120), world_pos=(session.party.x, session.party.y)
            )
            return
        damage = max(1, attack_roll - defense_roll)
        target.hp = max(0, target.hp - damage)
        session.append_log(f"{monster.name} hits you for {damage}. HP: {target.hp}/{target.max_hp}")
        self._set_feedback(
            session, f"You take {damage}", (255, 120, 120), world_pos=(session.party.x, session.party.y)
        )

    def _set_feedback(
        self,
        session: GameSession,
        text: str,
        color: tuple[int, int, int],
        ticks: int = 55,
        world_pos: tuple[int, int] | None = None,
    ) -> None:
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
            session.combat_feedback_text = None
            session.combat_feedback_world_pos = None

    def _npc_turn(self, session: GameSession) -> None:
        # Tiny movement jitter emulates non-player turns in place_exec.
        for monster in session.place.monsters:
            if not monster.is_alive():
                continue
            if abs(monster.x - session.party.x) + abs(monster.y - session.party.y) < 6:
                step_x = 1 if session.party.x > monster.x else -1 if session.party.x < monster.x else 0
                step_y = 1 if session.party.y > monster.y else -1 if session.party.y < monster.y else 0
                nx, ny = monster.x + step_x, monster.y + step_y
                if self._monster_can_enter_tile(session, monster, nx, ny):
                    monster.x, monster.y = nx, ny

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
