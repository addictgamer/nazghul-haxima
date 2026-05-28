from __future__ import annotations

import json
from pathlib import Path

from pygame_haxima.data.scm_parser import Expr, ScmParser, Symbol


class ScmConverter:
    """
    Minimal Phase-4 converter scaffold.

    This does not parse full Scheme. It extracts a few simple `(define key value)`
    declarations into JSON so data can be ported zone-by-zone.
    """

    BLOCKING_PCLASSES = {
        "pclass-wall",
        "pclass-repel",
        "pclass-space",
        "pclass-vmountains",
        "pclass-mountains",
        "pclass-boulder",
        "pclass-bars",
    }

    def __init__(self) -> None:
        self.parser = ScmParser()

    def convert_defines(self, src: Path, dst: Path) -> int:
        text = src.read_text(encoding="utf-8", errors="ignore")
        expressions = self.parser.parse_file(text)
        out: dict[str, str] = {}
        for expr in expressions:
            if not self._is_define(expr):
                continue
            define_expr = expr  # type: ignore[assignment]
            name = self._symbol_name(define_expr[1])
            if not name:
                continue
            out[name] = self._expr_to_string(define_expr[2])
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(out, indent=2), encoding="utf-8")
        return len(out)

    def convert_terrains(self, src: Path, dst: Path) -> int:
        text = src.read_text(encoding="utf-8", errors="ignore")
        expressions = self.parser.parse_file(text)
        env = self._build_constant_env(expressions)
        terrains_expr = self._find_define_value(expressions, "terrains")
        if terrains_expr is None:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(json.dumps({"terrains": []}, indent=2), encoding="utf-8")
            return 0
        terrain_entries = self._extract_list_entries(terrains_expr)
        converted: list[dict[str, object]] = []
        for entry in terrain_entries:
            terrain = self._convert_terrain_entry(entry, env)
            if terrain is not None:
                converted.append(terrain)
        payload = {
            "source": str(src),
            "terrain_count": len(converted),
            "terrains": converted,
        }
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return len(converted)

    def convert_map_file(self, src: Path, dst: Path) -> int:
        text = src.read_text(encoding="utf-8", errors="ignore")
        expressions = self.parser.parse_file(text)
        maps: list[dict[str, object]] = []
        for expr in expressions:
            if not isinstance(expr, list) or not expr:
                continue
            if self._symbol_name(expr[0]) != "kern-mk-map":
                continue
            parsed = self._convert_kern_mk_map(expr, src)
            if parsed is not None:
                maps.append(parsed)
        payload = {
            "source": str(src),
            "map_count": len(maps),
            "maps": maps,
        }
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return len(maps)

    def convert_place_file(self, src: Path, dst: Path) -> int:
        text = src.read_text(encoding="utf-8", errors="ignore")
        expressions = self.parser.parse_file(text)
        places: list[dict[str, object]] = []
        for expr in expressions:
            if not isinstance(expr, list) or not expr:
                continue
            if self._symbol_name(expr[0]) != "kern-mk-place":
                continue
            parsed = self._convert_kern_mk_place(expr, src)
            if parsed is not None:
                places.append(parsed)
        payload = {
            "source": str(src),
            "place_count": len(places),
            "places": places,
        }
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return len(places)

    def _build_constant_env(self, expressions: list[Expr]) -> dict[str, int | float | bool | None]:
        env: dict[str, int | float | bool | None] = {}
        for expr in expressions:
            if not self._is_define(expr):
                continue
            define_expr = expr  # type: ignore[assignment]
            name = self._symbol_name(define_expr[1])
            if name is None:
                continue
            value = self._resolve_value(define_expr[2], env)
            if isinstance(value, (int, float, bool)) or value is None:
                env[name] = value
        return env

    def _find_define_value(self, expressions: list[Expr], var_name: str) -> Expr | None:
        for expr in expressions:
            if not self._is_define(expr):
                continue
            define_expr = expr  # type: ignore[assignment]
            if self._symbol_name(define_expr[1]) == var_name:
                return define_expr[2]
        return None

    def _extract_list_entries(self, value_expr: Expr) -> list[list[Expr]]:
        if not isinstance(value_expr, list):
            return []
        if not value_expr:
            return []
        head = self._symbol_name(value_expr[0])
        if head != "list":
            return []
        entries: list[list[Expr]] = []
        for item in value_expr[1:]:
            if isinstance(item, list):
                entries.append(item)
        return entries

    def _convert_terrain_entry(
        self, entry: list[Expr], env: dict[str, int | float | bool | None]
    ) -> dict[str, object] | None:
        if not entry:
            return None
        if self._symbol_name(entry[0]) != "list":
            return None
        if len(entry) < 7:
            return None
        tag = self._resolve_to_symbol_string(entry[1], env)
        name = self._resolve_to_string(entry[2], env)
        pclass = self._resolve_to_symbol_string(entry[3], env)
        sprite = self._resolve_to_symbol_string(entry[4], env)
        opacity = self._resolve_to_number(entry[5], env)
        light = self._resolve_to_number(entry[6], env)
        step_on = None
        if len(entry) > 7:
            step_on = self._resolve_to_symbol_string(entry[7], env)
        if tag is None or name is None or pclass is None:
            return None
        return {
            "tag": tag,
            "name": name,
            "pclass": pclass,
            "sprite": sprite,
            "opacity": opacity,
            "light": light,
            "step_on": step_on,
            "passable": pclass not in self.BLOCKING_PCLASSES,
        }

    def _convert_kern_mk_map(self, expr: list[Expr], src: Path) -> dict[str, object] | None:
        # (kern-mk-map 'm_cloviskeep 64 64 pal_expanded (list "..."))
        if len(expr) < 6:
            return None
        map_id = self._resolve_to_symbol_string(expr[1], {})
        width = self._resolve_to_number(expr[2], {})
        height = self._resolve_to_number(expr[3], {})
        palette = self._resolve_to_symbol_string(expr[4], {})
        rows_expr = expr[5]
        rows = self._extract_map_rows(rows_expr)
        if map_id is None or width is None or height is None:
            return None
        token_rows = [self._tokenize_map_row(row) for row in rows]
        max_cols = max((len(r) for r in token_rows), default=0)
        return {
            "id": map_id,
            "width": int(width),
            "height": int(height),
            "palette": palette,
            "row_count": len(rows),
            "max_row_tokens": max_cols,
            "rows": rows,
            "tile_rows": token_rows,
            "source_file": src.name,
        }

    def _convert_kern_mk_place(self, expr: list[Expr], src: Path) -> dict[str, object] | None:
        # (kern-mk-place tag name sprite map wraps underground wilderness tmpcombat subplaces neighbors objects hooks entrances)
        if len(expr) < 11:
            return None
        place_id = self._resolve_to_symbol_string(expr[1], {})
        name = self._resolve_to_string(expr[2], {})
        sprite = self._resolve_to_symbol_string(expr[3], {})
        map_id = self._resolve_to_symbol_string(expr[4], {})
        wraps = self._resolve_to_bool(expr[5], {})
        underground = self._resolve_to_bool(expr[6], {})
        wilderness = self._resolve_to_bool(expr[7], {})
        tmp_combat = self._resolve_to_bool(expr[8], {})
        subplaces = self._extract_place_subplaces(expr[9] if len(expr) > 9 else None)
        neighbors = self._extract_symbol_list(expr[10] if len(expr) > 10 else None)
        objects_expr = expr[11] if len(expr) > 11 else None
        hooks_expr = expr[12] if len(expr) > 12 else None
        entrances_expr = expr[13] if len(expr) > 13 else None

        if place_id is None or name is None:
            return None
        objects_count = self._count_list_items(objects_expr)
        hooks = self._extract_symbol_list(hooks_expr)
        entrances_count = self._count_list_items(entrances_expr)
        return {
            "id": place_id,
            "name": name,
            "sprite": sprite,
            "map": map_id,
            "wraps": wraps,
            "underground": underground,
            "wilderness": wilderness,
            "tmp_combat": tmp_combat,
            "subplaces": subplaces,
            "neighbors": neighbors,
            "objects_count": objects_count,
            "on_entry_hooks": hooks,
            "entrances_count": entrances_count,
            "source_file": src.name,
        }

    def _extract_map_rows(self, rows_expr: Expr) -> list[str]:
        if not isinstance(rows_expr, list) or not rows_expr:
            return []
        if self._symbol_name(rows_expr[0]) != "list":
            return []
        rows: list[str] = []
        for entry in rows_expr[1:]:
            if isinstance(entry, str):
                rows.append(entry)
        return rows

    def _tokenize_map_row(self, row: str) -> list[str]:
        return [token for token in row.strip().split() if token]

    def _count_list_items(self, expr: Expr | None) -> int:
        if not isinstance(expr, list) or not expr:
            return 0
        if self._symbol_name(expr[0]) != "list":
            return 0
        return len(expr) - 1

    def _extract_place_subplaces(self, expr: Expr | None) -> list[dict[str, object]]:
        if not isinstance(expr, list) or not expr or self._symbol_name(expr[0]) != "list":
            return []
        out: list[dict[str, object]] = []
        for item in expr[1:]:
            if not isinstance(item, list) or len(item) < 3:
                continue
            if self._symbol_name(item[0]) != "list":
                continue
            place_id = self._resolve_to_symbol_string(item[1], {})
            x = self._resolve_to_number(item[2], {})
            y = self._resolve_to_number(item[3], {}) if len(item) > 3 else None
            out.append({"place": place_id, "x": x, "y": y})
        return out

    def _extract_symbol_list(self, expr: Expr | None) -> list[str]:
        if not isinstance(expr, list) or not expr:
            return []
        if self._symbol_name(expr[0]) != "list":
            return []
        out: list[str] = []
        for item in expr[1:]:
            sym = self._resolve_to_symbol_string(item, {})
            if sym is not None:
                out.append(sym)
        return out

    def _is_define(self, expr: Expr) -> bool:
        if not isinstance(expr, list) or len(expr) < 3:
            return False
        return self._symbol_name(expr[0]) == "define"

    def _symbol_name(self, expr: Expr) -> str | None:
        if isinstance(expr, Symbol):
            return expr.name
        return None

    def _resolve_value(
        self, expr: Expr, env: dict[str, int | float | bool | None]
    ) -> int | float | bool | None | str:
        if isinstance(expr, (int, float, bool)) or expr is None:
            return expr
        if isinstance(expr, Symbol):
            if expr.name in env:
                return env[expr.name]
            return expr.name
        if isinstance(expr, str):
            return expr
        if isinstance(expr, list) and len(expr) == 2 and self._symbol_name(expr[0]) == "quote":
            inner = expr[1]
            if isinstance(inner, Symbol):
                return inner.name
            return str(inner)
        return str(expr)

    def _resolve_to_symbol_string(
        self, expr: Expr, env: dict[str, int | float | bool | None]
    ) -> str | None:
        value = self._resolve_value(expr, env)
        if isinstance(value, str):
            return value
        return None

    def _resolve_to_string(self, expr: Expr, env: dict[str, int | float | bool | None]) -> str | None:
        value = self._resolve_value(expr, env)
        if isinstance(value, str):
            return value
        return None

    def _resolve_to_number(
        self, expr: Expr, env: dict[str, int | float | bool | None]
    ) -> int | float | None:
        value = self._resolve_value(expr, env)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return value
        return None

    def _resolve_to_bool(self, expr: Expr, env: dict[str, int | float | bool | None]) -> bool | None:
        value = self._resolve_value(expr, env)
        if isinstance(value, bool):
            return value
        return None

    def _expr_to_string(self, expr: Expr) -> str:
        if isinstance(expr, Symbol):
            return expr.name
        if isinstance(expr, str):
            return expr
        if isinstance(expr, bool):
            return "#t" if expr else "#f"
        if expr is None:
            return "nil"
        if isinstance(expr, (int, float)):
            return str(expr)
        if isinstance(expr, list):
            if len(expr) == 2 and self._symbol_name(expr[0]) == "quote":
                return "'" + self._expr_to_string(expr[1])
            inner = " ".join(self._expr_to_string(part) for part in expr)
            return f"({inner})"
        return str(expr)
