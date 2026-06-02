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
    facing: str = "s"

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
    reagents: dict[str, int] = field(
        default_factory=lambda: {
            "sulphurous_ash": 2,
            "ginseng": 1,
            "garlic": 1,
        }
    )
    spells_known: list[str] = field(default_factory=lambda: ["spark", "heal", "ward"])
    selected_spell: str = "spark"
    ward_charges: int = 0

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
class Trap:
    trap_id: str
    x: int
    y: int
    detected: bool = False
    disarmed: bool = False


@dataclass
class TileField:
    x: int
    y: int
    field_kind: str
    turns_remaining: int


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
    traps: list[Trap] = field(default_factory=list)
    ground_items: dict[tuple[int, int], list[Item]] = field(default_factory=dict)
    tile_fields: dict[tuple[int, int], TileField] = field(default_factory=dict)
    spell_context: str = "context-town"

    def field_at(self, x: int, y: int) -> TileField | None:
        return self.tile_fields.get((x, y))

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

    def trap_at(self, x: int, y: int) -> Trap | None:
        for trap in self.traps:
            if (trap.x, trap.y) == (x, y) and not trap.disarmed:
                return trap
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
    show_reagents_menu: bool = False
    show_spellbook_menu: bool = False
    spellbook_tab: str = "all"
    spellbook_selected_index: int = 0
    spellbook_hover_index: int | None = None
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
    combat_feedback_lines: list[tuple[str, tuple[int, int, int]]] = field(default_factory=list)
    ui_anim_tick: int = 0
    camera_start_x: int | None = None
    camera_start_y: int | None = None
    camera_deadzone_tiles: int = 4

    def append_log(self, message: str) -> None:
        self.log_lines.append(message)
        self.log_lines = self.log_lines[-100:]

    def advance_turn(self, minutes: int = 5) -> None:
        for buff_key in (
            "buff:light_turns",
            "buff:quickness_turns",
            "buff:invisible_turns",
            "buff:ensnare_turns",
        ):
            buff_turns = self.quest_flags.get(buff_key)
            if isinstance(buff_turns, int) and not isinstance(buff_turns, bool):
                remaining = max(0, buff_turns - 1)
                if remaining > 0:
                    self.quest_flags[buff_key] = remaining
                else:
                    self.quest_flags.pop(buff_key, None)
        expired_confuse: list[str] = []
        for key, value in self.quest_flags.items():
            if not key.startswith("confuse:") or not isinstance(value, int) or isinstance(value, bool):
                continue
            remaining = max(0, value - 1)
            if remaining > 0:
                self.quest_flags[key] = remaining
            else:
                expired_confuse.append(key)
        for key in expired_confuse:
            self.quest_flags.pop(key, None)
        expired_summons: list[str] = []
        monsters_by_id = {monster.entity_id: monster for monster in self.place.monsters}
        for key, value in self.quest_flags.items():
            if not key.startswith("summon:") or not isinstance(value, int) or isinstance(value, bool):
                continue
            entity_id = key.removeprefix("summon:")
            remaining = max(0, value - 1)
            if remaining > 0:
                self.quest_flags[key] = remaining
            else:
                expired_summons.append(entity_id)
        for entity_id in expired_summons:
            self.quest_flags.pop(f"summon:{entity_id}", None)
            monster = monsters_by_id.get(entity_id)
            if monster is not None and not monster.hostile:
                monster.hp = 0
                self.append_log(f"{monster.name} fades away.")
        expired_fields: list[tuple[int, int]] = []
        for pos, tile_field in self.place.tile_fields.items():
            tile_field.turns_remaining -= 1
            if tile_field.turns_remaining <= 0:
                expired_fields.append(pos)
        for pos in expired_fields:
            self.place.tile_fields.pop(pos, None)
        expired_mind: list[str] = []
        for key, value in self.quest_flags.items():
            if not (
                key.startswith("sleep:")
                or key.startswith("fear:")
                or key.startswith("charm:")
                or key.startswith("ensnare:")
            ):
                continue
            if not isinstance(value, int) or isinstance(value, bool):
                continue
            remaining = max(0, value - 1)
            if remaining > 0:
                self.quest_flags[key] = remaining
            else:
                expired_mind.append(key)
        for key in expired_mind:
            self.quest_flags.pop(key, None)
        expired_monster_poison: list[str] = []
        monsters_by_id = {monster.entity_id: monster for monster in self.place.monsters}
        for key, value in self.quest_flags.items():
            if not key.startswith("poison:") or not isinstance(value, int) or isinstance(value, bool):
                continue
            entity_id = key.removeprefix("poison:")
            monster = monsters_by_id.get(entity_id)
            if monster is not None and monster.is_alive():
                monster.hp = max(0, monster.hp - 1)
                self.append_log(f"{monster.name} suffers 1 poison damage.")
                if not monster.is_alive():
                    self.append_log(f"{monster.name} is defeated.")
                    self.quest_flags[f"defeated:{entity_id}"] = True
            remaining = max(0, value - 1)
            if remaining > 0:
                self.quest_flags[key] = remaining
            else:
                expired_monster_poison.append(key)
        for key in expired_monster_poison:
            self.quest_flags.pop(key, None)
        if any(not monster.is_alive() for monster in self.place.monsters):
            self.victory = all(not monster.is_alive() for monster in self.place.monsters)
        self.party.turn_count += 1
        party_poison = self.quest_flags.get("buff:poison_turns")
        if isinstance(party_poison, int) and not isinstance(party_poison, bool) and party_poison > 0:
            lead = self.party.lead()
            lead.hp = max(0, lead.hp - 1)
            self.append_log(f"You take 1 poison damage. HP: {lead.hp}/{lead.max_hp}")
            remaining = party_poison - 1
            if remaining > 0:
                self.quest_flags["buff:poison_turns"] = remaining
            else:
                self.quest_flags.pop("buff:poison_turns", None)
        total = self.clock_hours * 60 + self.clock_minutes + minutes
        self.clock_hours = (total // 60) % 24
        self.clock_minutes = total % 60
