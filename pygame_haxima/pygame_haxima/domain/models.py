from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Mode(str, Enum):
    EXPLORE = "explore"
    COMBAT = "combat"
    TALK = "talk"


@dataclass(frozen=True)
class Terrain:
    terrain_id: str
    name: str
    passable: bool
    glyph: str
    color: tuple[int, int, int]
    sprite_key: str | None = None


@dataclass
class Tile:
    terrain_id: str
    discovered: bool = True


@dataclass
class Item:
    item_id: str
    name: str
    value: int = 0
    sprite_key: str | None = None


@dataclass
class Entity:
    entity_id: str
    name: str
    x: int
    y: int
    sprite_key: str
    hp: int = 10
    max_hp: int = 10
    ap: int = 50
    attack: int = 3
    defense: int = 1
    hostile: bool = False

    def is_alive(self) -> bool:
        return self.hp > 0


@dataclass
class Party:
    x: int
    y: int
    members: list[Entity] = field(default_factory=list)
    inventory: list[Item] = field(default_factory=list)
    gold: int = 20
    food: int = 100
    turn_count: int = 0

    def lead(self) -> Entity:
        return self.members[0]


@dataclass
class Npc:
    npc_id: str
    name: str
    x: int
    y: int
    sprite_key: str
    keywords: dict[str, str]


@dataclass
class Chest:
    chest_id: str
    x: int
    y: int
    sprite_key: str = "s_chest"
    items: list[Item] = field(default_factory=list)
    opened: bool = False


@dataclass
class Place:
    place_id: str
    name: str
    width: int
    height: int
    terrain_defs: dict[str, Terrain]
    tiles: list[list[Tile]]
    npcs: list[Npc] = field(default_factory=list)
    monsters: list[Entity] = field(default_factory=list)
    chests: list[Chest] = field(default_factory=list)
    ground_items: dict[tuple[int, int], list[Item]] = field(default_factory=dict)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def terrain_at(self, x: int, y: int) -> Terrain:
        tile = self.tiles[y][x]
        return self.terrain_defs[tile.terrain_id]

    def passable(self, x: int, y: int) -> bool:
        if not self.in_bounds(x, y):
            return False
        terrain = self.terrain_at(x, y)
        if not terrain.passable:
            return False
        for monster in self.monsters:
            if monster.is_alive() and (monster.x, monster.y) == (x, y):
                return False
        return True

    def chest_at(self, x: int, y: int) -> Chest | None:
        for chest in self.chests:
            if (chest.x, chest.y) == (x, y):
                return chest
        return None

    def npc_at(self, x: int, y: int) -> Npc | None:
        for npc in self.npcs:
            if (npc.x, npc.y) == (x, y):
                return npc
        return None

    def monster_at(self, x: int, y: int) -> Entity | None:
        for monster in self.monsters:
            if monster.is_alive() and (monster.x, monster.y) == (x, y):
                return monster
        return None


@dataclass
class CombatState:
    active: bool = False
    message: str = ""
    enemy_ids: list[str] = field(default_factory=list)


@dataclass
class GameSession:
    place: Place
    party: Party
    mode: Mode = Mode.EXPLORE
    clock_hours: int = 7
    clock_minutes: int = 0
    log_lines: list[str] = field(default_factory=list)
    command_prompt: str = "Command>"
    target_cursor: tuple[int, int] | None = None
    targeting_action: str | None = None
    selected_npc_id: str | None = None
    combat: CombatState = field(default_factory=CombatState)
    running: bool = True
    victory: bool = False
    debug_terrain_ids: bool = False
    debug_sprite_warnings: bool = False
    debug_runtime_state: bool = False
    terrain_fallback_key_count: int = 0
    terrain_fallback_keys: list[str] = field(default_factory=list)
    show_options_menu: bool = False
    options_selected_index: int = 0
    show_save_load_menu: bool = False
    save_load_mode: str | None = None
    save_load_selected_slot: int = 0
    save_slot_labels: list[str] = field(default_factory=list)
    option_scale: int = 1
    option_fullscreen: bool = False
    keybind_preview: list[str] = field(default_factory=list)
    dialogue_speaker: str | None = None
    dialogue_lines: list[str] = field(default_factory=list)
    npc_states: dict[str, dict[str, object]] = field(default_factory=dict)
    quest_flags: dict[str, object] = field(default_factory=dict)
    combat_feedback_text: str | None = None
    combat_feedback_ticks: int = 0
    combat_feedback_color: tuple[int, int, int] = (240, 220, 150)
    combat_feedback_world_pos: tuple[int, int] | None = None
    ui_anim_tick: int = 0
    camera_start_x: int | None = None
    camera_start_y: int | None = None
    camera_deadzone_tiles: int = 4

    def append_log(self, message: str) -> None:
        self.log_lines.append(message)
        self.log_lines = self.log_lines[-100:]

    def advance_turn(self, minutes: int = 5) -> None:
        self.party.turn_count += 1
        total = self.clock_hours * 60 + self.clock_minutes + minutes
        self.clock_hours = (total // 60) % 24
        self.clock_minutes = total % 60
