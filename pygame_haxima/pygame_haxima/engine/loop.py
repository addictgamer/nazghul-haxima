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
            if event.kind == EngineEventType.MOUSE_TILE:
                self._handle_mouse_move(session, event.payload["tile"])
                continue
            if event.kind != EngineEventType.ACTION:
                continue
            action = event.payload["action"]
            if action == "options_menu":
                self._toggle_options_menu(session)
                continue
            if session.show_options_menu:
                self._handle_options_menu_action(session, action)
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
                self._talk(session)
            elif action == "open":
                self._open_chest(session)
            elif action == "get":
                self._get_items(session)
            elif action == "attack":
                self._attack(session)
            elif action == "examine":
                self._examine(session)
            elif action == "save":
                path = self.save_manager.save(session)
                session.append_log(f"Saved game to {path.name}.")
            elif action == "load":
                loaded = self.save_manager.load(session)
                session.append_log("Loaded saved game." if loaded else "No saved game found.")
            elif action == "help":
                self._help(session)
            elif action == "cancel":
                session.target_cursor = None
                session.command_prompt = "Command> (H help, F10 options)"
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

    def _handle_mouse_move(self, session: GameSession, tile: tuple[int, int]) -> None:
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
        if not session.place.passable(nx, ny):
            session.append_log("Blocked.")
            return
        session.party.x, session.party.y = nx, ny
        session.party.members[0].x, session.party.members[0].y = nx, ny
        session.advance_turn()
        session.party.food = max(0, session.party.food - 1)
        self._check_auto_combat(session)
        self._npc_turn(session)

    def _talk(self, session: GameSession) -> None:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            npc = session.place.npc_at(session.party.x + dx, session.party.y + dy)
            if npc is None:
                continue
            session.mode = Mode.TALK
            session.append_log(f"{npc.name}: {npc.keywords.get('name', 'Greetings.')}")
            session.append_log(f"{npc.name}: {npc.keywords.get('job', 'I wander.')}")
            session.append_log(f"{npc.name}: {npc.keywords.get('bye', 'Farewell.')}")
            session.mode = Mode.EXPLORE
            session.advance_turn()
            return
        session.append_log("No one nearby to talk to.")

    def _open_chest(self, session: GameSession) -> None:
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            chest = session.place.chest_at(session.party.x + dx, session.party.y + dy)
            if chest is None:
                continue
            if chest.opened:
                session.append_log("Chest is already open.")
                return
            chest.opened = True
            if chest.items:
                session.place.ground_items[(chest.x, chest.y)] = list(chest.items)
            session.append_log("You open the chest. Items spill onto the ground.")
            session.advance_turn()
            return
        session.append_log("No chest nearby.")

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

    def _attack(self, session: GameSession) -> None:
        monster = self._adjacent_monster(session)
        if monster is None:
            session.append_log("No enemy in range.")
            return
        session.mode = Mode.COMBAT
        self._resolve_combat_round(session, monster)
        if not monster.is_alive():
            session.append_log(f"{monster.name} falls.")
            session.victory = True
            session.mode = Mode.EXPLORE
            return
        self._enemy_counterattack(session, monster)
        if session.party.lead().hp <= 0:
            session.append_log("The Wanderer has fallen. Game over.")
            session.running = False
            return
        session.mode = Mode.EXPLORE
        session.advance_turn()

    def _examine(self, session: GameSession) -> None:
        terrain = session.place.terrain_at(session.party.x, session.party.y)
        session.append_log(f"You are on {terrain.name}.")
        if session.party.inventory:
            session.append_log("Inventory: " + ", ".join(item.name for item in session.party.inventory))
        else:
            session.append_log("Inventory is empty.")

    def _help(self, session: GameSession) -> None:
        session.append_log("Move: arrows/WASD | t talk | o open | g get | f attack | x examine")
        session.append_log(
            "F5 save | F9 load | F10 options | F11 fullscreen | F2 terrain IDs | F3 sprite warnings"
        )

    def _toggle_options_menu(self, session: GameSession) -> None:
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
            return
        damage = max(1, attack_roll - defense_roll)
        monster.hp = max(0, monster.hp - damage)
        session.append_log(f"You hit {monster.name} for {damage} damage.")
        self.audio.play_effect("sounds/hit.wav")

    def _enemy_counterattack(self, session: GameSession, monster: Entity) -> None:
        if not monster.is_alive():
            return
        target = session.party.lead()
        attack_roll = random.randint(1, 6) + monster.attack
        defense_roll = random.randint(1, 6) + target.defense
        if attack_roll <= defense_roll:
            session.append_log(f"{monster.name} misses.")
            return
        damage = max(1, attack_roll - defense_roll)
        target.hp = max(0, target.hp - damage)
        session.append_log(f"{monster.name} hits you for {damage}. HP: {target.hp}/{target.max_hp}")

    def _npc_turn(self, session: GameSession) -> None:
        # Tiny movement jitter emulates non-player turns in place_exec.
        for monster in session.place.monsters:
            if not monster.is_alive():
                continue
            if abs(monster.x - session.party.x) + abs(monster.y - session.party.y) < 6:
                step_x = 1 if session.party.x > monster.x else -1 if session.party.x < monster.x else 0
                step_y = 1 if session.party.y > monster.y else -1 if session.party.y < monster.y else 0
                nx, ny = monster.x + step_x, monster.y + step_y
                if session.place.passable(nx, ny):
                    monster.x, monster.y = nx, ny
