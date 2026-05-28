from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pygame

from pygame_haxima.config import DISPLAY
from pygame_haxima.data.asset_loader import AssetLoader

SPRITE_RE = re.compile(
    r"\(kern-mk-sprite\s+'(?P<name>[^\s]+)\s+(?P<set>[^\s]+)\s+(?P<frames>\d+)\s+(?P<index>\d+)\s+[#tf]+\s+\d+\s*\)"
)
SPELL_MK_SPRITE_RE = re.compile(
    r"\(mk-sprite\s+'(?P<name>[^\s]+)\s+(?P<index>\d+)\s*\)"
)
SPRITE_SET_RE = re.compile(
    r'\(kern-mk-sprite-set\s+\'(?P<name>[^\s]+)\s+'
    r"(?P<tile_w>\d+)\s+(?P<tile_h>\d+)\s+"
    r"(?P<rows>\d+)\s+(?P<cols>\d+)\s+"
    r"(?P<xoff>\d+)\s+(?P<yoff>\d+)\s+"
    r'"(?P<filename>[^"]+)"\s*\)'
)


@dataclass(frozen=True)
class SpriteRef:
    key: str
    sprite_set: str
    frame_count: int
    tile_index: int


@dataclass(frozen=True)
class SpriteSetRef:
    name: str
    tile_w: int
    tile_h: int
    cols: int
    rows: int
    xoff: int
    yoff: int
    filename: str


class SpriteAtlas:
    def __init__(self, asset_loader: AssetLoader, project_root: Path) -> None:
        self.asset_loader = asset_loader
        self.project_root = project_root
        self.refs: dict[str, SpriteRef] = {}
        self.sprite_sets: dict[str, SpriteSetRef] = {}
        self.surfaces: dict[str, pygame.Surface] = {}
        self.resolved_keys: set[str] = set()
        self.fallback_keys: set[str] = set()
        self.missing_sprite_set_keys: set[str] = set()
        self.missing_sheet_keys: set[str] = set()
        self.out_of_bounds_keys: set[str] = set()
        self.missing_sheet_files: set[str] = set()
        self._tile_w = DISPLAY.tile_w
        self._tile_h = DISPLAY.tile_h

    def load(self) -> None:
        self._parse_sprite_sets()
        self._parse_sprite_refs()
        self.resolved_keys.clear()
        self.fallback_keys.clear()
        self.missing_sprite_set_keys.clear()
        self.missing_sheet_keys.clear()
        self.out_of_bounds_keys.clear()
        self.missing_sheet_files.clear()

        for key in self.refs:
            surface, reason = self._extract_surface(key)
            if surface is not None:
                self.resolved_keys.add(key)
                self.surfaces[key] = surface
                continue
            self.fallback_keys.add(key)
            self.surfaces[key] = self._fallback_surface(key)
            if reason == "missing_sprite_set":
                self.missing_sprite_set_keys.add(key)
            elif reason == "missing_sheet":
                self.missing_sheet_keys.add(key)
            elif reason == "out_of_bounds":
                self.out_of_bounds_keys.add(key)

        for fallback in (
            "s_grass",
            "s_wall",
            "s_wanderer",
            "s_old_townsman",
            "s_chest",
            "s_wolf",
            "s_dagger",
            "s_leather_armor",
            "s_healing_potion",
            "s_gold_coins",
            "s_gem",
        ):
            self.surfaces.setdefault(fallback, self._fallback_surface(fallback))

    def _active_lines(self, path: Path) -> list[str]:
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines: list[str] = []
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith(";"):
                continue
            lines.append(stripped)
        return lines

    def _parse_sprite_sets(self) -> None:
        for scm_path in self._iter_world_scm_paths():
            for line in self._active_lines(scm_path):
                match = SPRITE_SET_RE.match(line)
                if not match:
                    continue
                ref = SpriteSetRef(
                    name=match.group("name"),
                    tile_w=int(match.group("tile_w")),
                    tile_h=int(match.group("tile_h")),
                    cols=int(match.group("cols")),
                    rows=int(match.group("rows")),
                    xoff=int(match.group("xoff")),
                    yoff=int(match.group("yoff")),
                    filename=match.group("filename"),
                )
                self.sprite_sets[ref.name] = ref

    def _parse_sprite_refs(self) -> None:
        for scm_path in self._iter_world_scm_paths():
            for line in self._active_lines(scm_path):
                match = SPRITE_RE.match(line)
                if match:
                    key = match.group("name")
                    self.refs[key] = SpriteRef(
                        key=key,
                        sprite_set=match.group("set"),
                        frame_count=max(1, int(match.group("frames"))),
                        tile_index=int(match.group("index")),
                    )
                    continue
                spell_match = SPELL_MK_SPRITE_RE.match(line)
                if spell_match and scm_path.name == "spells.scm":
                    key = spell_match.group("name")
                    self.refs[key] = SpriteRef(
                        key=key,
                        sprite_set="ss_spells",
                        frame_count=1,
                        tile_index=int(spell_match.group("index")),
                    )

    def _iter_world_scm_paths(self) -> list[Path]:
        world_dir = self.project_root.parent / "worlds" / "haxima-1.002"
        return sorted(world_dir.rglob("*.scm"))

    def _extract_surface(self, key: str) -> tuple[pygame.Surface | None, str | None]:
        return self._extract_surface_for_frame(key, 0)

    def _extract_surface_for_frame(self, key: str, frame_offset: int) -> tuple[pygame.Surface | None, str | None]:
        sprite_ref = self.refs.get(key)
        if sprite_ref is None:
            return None, "missing_ref"
        sprite_set = self.sprite_sets.get(sprite_ref.sprite_set)
        if sprite_set is None:
            return None, "missing_sprite_set"
        sheet = self.asset_loader.load_image(sprite_set.filename)
        if sheet is None:
            self.missing_sheet_files.add(sprite_set.filename)
            return None, "missing_sheet"
        tile_index = sprite_ref.tile_index + max(0, frame_offset)
        col = tile_index % sprite_set.cols
        row = tile_index // sprite_set.cols
        if row >= sprite_set.rows:
            return None, "out_of_bounds"
        src = pygame.Rect(
            sprite_set.xoff + col * sprite_set.tile_w,
            sprite_set.yoff + row * sprite_set.tile_h,
            sprite_set.tile_w,
            sprite_set.tile_h,
        )
        if src.right > sheet.get_width() or src.bottom > sheet.get_height():
            return None, "out_of_bounds"
        tile = pygame.Surface((self._tile_w, self._tile_h), pygame.SRCALPHA)
        tile.blit(sheet, (0, 0), src)
        if (sprite_set.tile_w, sprite_set.tile_h) != (self._tile_w, self._tile_h):
            tile = pygame.transform.scale(tile, (self._tile_w, self._tile_h))
        return tile, None

    def _fallback_surface(self, key: str) -> pygame.Surface:
        surface = pygame.Surface((self._tile_w, self._tile_h), pygame.SRCALPHA)
        base = abs(hash(key)) % 200 + 30
        color = (base % 255, (base * 2) % 255, (base * 3) % 255)
        surface.fill(color)
        pygame.draw.rect(surface, (20, 20, 20), surface.get_rect(), 1)
        return surface

    def get(self, key: str) -> pygame.Surface:
        return self.surfaces.get(key, self.surfaces["s_grass"])

    def get_for_tick(self, key: str, tick: int, frame_stride: int = 8) -> pygame.Surface:
        sprite_ref = self.refs.get(key)
        if sprite_ref is None or sprite_ref.frame_count <= 1:
            return self.get(key)
        frame = (tick // max(1, frame_stride)) % sprite_ref.frame_count
        if frame == 0:
            return self.get(key)
        cache_key = f"{key}#f{frame}"
        cached = self.surfaces.get(cache_key)
        if cached is not None:
            return cached
        surface, _reason = self._extract_surface_for_frame(key, frame)
        if surface is None:
            return self.get(key)
        self.surfaces[cache_key] = surface
        return surface

    def has_key(self, key: str) -> bool:
        return key in self.refs or key in self.surfaces

    def is_fallback(self, key: str) -> bool:
        return key in self.fallback_keys

    def coverage_report(self) -> dict[str, object]:
        return {
            "sprite_sets": len(self.sprite_sets),
            "sprite_refs": len(self.refs),
            "resolved_keys": len(self.resolved_keys),
            "fallback_keys": len(self.fallback_keys),
            "missing_sprite_set_keys": sorted(self.missing_sprite_set_keys),
            "missing_sheet_keys": sorted(self.missing_sheet_keys),
            "missing_sheet_files": sorted(self.missing_sheet_files),
            "out_of_bounds_keys": sorted(self.out_of_bounds_keys),
        }

    def runtime_coverage_report(self, runtime_keys: Iterable[str]) -> dict[str, object]:
        keys = sorted({key for key in runtime_keys if key})
        direct_resolved: list[str] = []
        alias_resolved: dict[str, str] = {}
        unresolved_aliases: dict[str, str] = {}
        fallback_runtime_keys: list[str] = []
        missing_runtime_keys: list[str] = []
        for key in keys:
            if self._has_sprite_key(key):
                direct_resolved.append(key)
                if self.is_fallback(key):
                    fallback_runtime_keys.append(key)
                continue
            alias_target = self._alias_target(key)
            if alias_target is None:
                missing_runtime_keys.append(key)
                continue
            if self._has_sprite_key(alias_target):
                alias_resolved[key] = alias_target
                if self.is_fallback(alias_target):
                    fallback_runtime_keys.append(key)
                continue
            unresolved_aliases[key] = alias_target
        return {
            "runtime_keys": keys,
            "direct_resolved": direct_resolved,
            "alias_resolved": alias_resolved,
            "unresolved_aliases": unresolved_aliases,
            "fallback_runtime_keys": sorted(set(fallback_runtime_keys)),
            "missing_runtime_keys": missing_runtime_keys,
        }

    def format_runtime_coverage_report(self, runtime_keys: Iterable[str]) -> str:
        report = self.runtime_coverage_report(runtime_keys)
        lines = [
            "Runtime Sprite Coverage",
            f"- runtime_keys: {len(report['runtime_keys'])}",
            f"- direct_resolved: {len(report['direct_resolved'])}",
            f"- alias_resolved: {len(report['alias_resolved'])}",
            f"- unresolved_aliases: {len(report['unresolved_aliases'])}",
            f"- fallback_runtime_keys: {len(report['fallback_runtime_keys'])}",
            f"- missing_runtime_keys: {len(report['missing_runtime_keys'])}",
        ]
        unresolved_aliases = report["unresolved_aliases"]
        if unresolved_aliases:
            preview = ", ".join(
                f"{src}->{dst}" for src, dst in list(unresolved_aliases.items())[:6]
            )
            lines.append(f"- unresolved_alias_preview: {preview}")
        missing_keys = report["missing_runtime_keys"]
        if missing_keys:
            lines.append(f"- missing_runtime_preview: {', '.join(missing_keys[:6])}")
        return "\n".join(lines) + "\n"

    def format_coverage_report(self) -> str:
        report = self.coverage_report()
        lines = [
            "Sprite Coverage Report",
            f"- sprite_sets: {report['sprite_sets']}",
            f"- sprite_refs: {report['sprite_refs']}",
            f"- resolved_keys: {report['resolved_keys']}",
            f"- fallback_keys: {report['fallback_keys']}",
        ]
        missing_files = report["missing_sheet_files"]
        if missing_files:
            lines.append(f"- missing_sheet_files: {', '.join(missing_files)}")
        if report["missing_sprite_set_keys"]:
            lines.append(f"- missing_sprite_set_keys: {len(report['missing_sprite_set_keys'])}")
        if report["missing_sheet_keys"]:
            lines.append(f"- missing_sheet_keys: {len(report['missing_sheet_keys'])}")
        if report["out_of_bounds_keys"]:
            lines.append(f"- out_of_bounds_keys: {len(report['out_of_bounds_keys'])}")
        return "\n".join(lines) + "\n"

    def write_coverage_report(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.format_coverage_report(), encoding="utf-8")

    def _has_sprite_key(self, key: str) -> bool:
        return key in self.refs or key in self.surfaces

    def _alias_target(self, key: str) -> str | None:
        if "-" in key:
            candidate = key.replace("-", "_")
            if candidate != key:
                return candidate
        for suffix in ("_n", "_s", "_e", "_w", "_ne", "_nw", "_se", "_sw", "_asleep"):
            if key.endswith(suffix):
                candidate = key[: -len(suffix)]
                if candidate:
                    return candidate
        return None
