from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pygame_haxima.data.scm_converter import ScmConverter


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    world = root.parent / "worlds" / "haxima-1.002"
    output = root / "converted_data"
    converter = ScmConverter()
    validation_warnings: list[str] = []
    report_sections: dict[str, object] = {}

    targets = {
        "terrains.scm": ("terrains.runtime.json", converter.convert_terrains),
        "palette.scm": ("palettes.runtime.json", converter.convert_palette_file),
        "zones.scm": ("zones.defines.json", converter.convert_defines),
        "world-map.scm": ("world-map.defines.json", converter.convert_defines),
    }
    core_exports: list[dict[str, object]] = []
    for rel, (output_name, convert_fn) in targets.items():
        src = world / rel
        if not src.exists():
            print(f"skip: {src}")
            continue
        dst = output / output_name
        count = convert_fn(src, dst)
        core_exports.append({"source": src.name, "output": output_name, "count": count})
        print(f"converted {src.name}: {count} entries -> {dst.name}")
    report_sections["core_exports"] = core_exports

    maps_dir = world / "maps"
    maps_out_dir = output / "maps"
    map_files = sorted(maps_dir.glob("*.scm"))
    map_index: list[dict[str, object]] = []
    for map_file in map_files:
        out_file = maps_out_dir / f"{map_file.stem}.map.json"
        count = converter.convert_map_file(map_file, out_file)
        map_index.append({"source": map_file.name, "output": out_file.name, "map_count": count})
        if count == 0:
            validation_warnings.append(f"maps/{map_file.name}: no kern-mk-map forms converted")
        print(f"converted {map_file.name}: {count} map(s) -> maps/{out_file.name}")
    (maps_out_dir / "index.json").write_text(json.dumps(map_index, indent=2), encoding="utf-8")
    print(f"wrote maps index: maps/index.json ({len(map_index)} files)")
    map_dimension_checks = _validate_map_dimensions(maps_out_dir, map_index, validation_warnings)
    report_sections["maps"] = {
        "files_seen": len(map_files),
        "index_count": len(map_index),
        "index": map_index,
        "dimension_checks": map_dimension_checks,
    }

    places_dir = world / "places"
    places_out_dir = output / "places"
    place_files = sorted(places_dir.glob("*.scm"))
    place_index: list[dict[str, object]] = []
    for place_file in place_files:
        out_file = places_out_dir / f"{place_file.stem}.place.json"
        count = converter.convert_place_file(place_file, out_file)
        place_index.append({"source": place_file.name, "output": out_file.name, "place_count": count})
        if count == 0:
            validation_warnings.append(f"places/{place_file.name}: no kern-mk-place forms converted")
        print(f"converted {place_file.name}: {count} place(s) -> places/{out_file.name}")
    (places_out_dir / "index.json").write_text(json.dumps(place_index, indent=2), encoding="utf-8")
    print(f"wrote places index: places/index.json ({len(place_index)} files)")
    report_sections["places"] = {
        "files_seen": len(place_files),
        "index_count": len(place_index),
        "index": place_index,
    }

    townsfolk_init = world / "townsfolk" / "init.scm"
    townsfolk_out = output / "townsfolk.runtime.json"
    townsfolk_summary: dict[str, object] = {"source": str(townsfolk_init), "converted_count": 0}
    if townsfolk_init.exists():
        count = converter.convert_townsfolk(world, townsfolk_init, townsfolk_out)
        townsfolk_summary["converted_count"] = count
        townsfolk_payload = json.loads(townsfolk_out.read_text(encoding="utf-8"))
        unresolved = townsfolk_payload.get("unresolved_loads", [])
        if isinstance(unresolved, list) and unresolved:
            for item in unresolved:
                validation_warnings.append(f"townsfolk unresolved load: {item}")
        townsfolk_summary["loaded_count"] = townsfolk_payload.get("loaded_count", 0)
        townsfolk_summary["resolved_count"] = townsfolk_payload.get("resolved_count", 0)
        townsfolk_summary["unresolved_loads"] = unresolved
        print(f"converted townsfolk: {count} files -> {townsfolk_out.name}")
    else:
        validation_warnings.append("townsfolk init missing: townsfolk/init.scm")
        print(f"skip: {townsfolk_init}")

    report_sections["townsfolk"] = townsfolk_summary

    quests_dir = world
    quests_out_dir = output / "quests"
    quest_files = sorted(quests_dir.glob("quests-*.scm"))
    quest_index: list[dict[str, object]] = []
    for quest_file in quest_files:
        out_file = quests_out_dir / f"{quest_file.stem}.quests.json"
        count = converter.convert_quest_file(quest_file, out_file)
        quest_payload = json.loads(out_file.read_text(encoding="utf-8"))
        update_refs = quest_payload.get("quest_update_refs", [])
        update_ref_count = len(update_refs) if isinstance(update_refs, list) else 0
        quest_index.append(
            {
                "source": quest_file.name,
                "output": out_file.name,
                "quest_count": count,
                "update_ref_count": update_ref_count,
            }
        )
        if count == 0 and update_ref_count == 0:
            validation_warnings.append(
                f"quests/{quest_file.name}: no qst-mk quest entries or quest-data updates converted"
            )
        print(f"converted {quest_file.name}: {count} quest(s) -> quests/{out_file.name}")
    (quests_out_dir / "index.json").write_text(json.dumps(quest_index, indent=2), encoding="utf-8")
    print(f"wrote quests index: quests/index.json ({len(quest_index)} files)")
    report_sections["quests"] = {
        "files_seen": len(quest_files),
        "index_count": len(quest_index),
        "index": quest_index,
    }
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "world_dir": str(world),
        "output_dir": str(output),
        "sections": report_sections,
        "warning_count": len(validation_warnings),
        "warnings": validation_warnings,
    }
    report_file = output / "import_validation_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote validation report: {report_file.name} ({len(validation_warnings)} warnings)")
    return 0


def _validate_map_dimensions(
    maps_out_dir: Path, map_index: list[dict[str, object]], validation_warnings: list[str]
) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    for record in map_index:
        output_name = record.get("output")
        if not isinstance(output_name, str):
            continue
        payload_file = maps_out_dir / output_name
        if not payload_file.exists():
            validation_warnings.append(f"maps/{output_name}: output file missing")
            continue
        payload = json.loads(payload_file.read_text(encoding="utf-8"))
        maps = payload.get("maps", [])
        if not isinstance(maps, list):
            validation_warnings.append(f"maps/{output_name}: malformed map payload")
            continue
        for entry in maps:
            if not isinstance(entry, dict):
                continue
            map_id = str(entry.get("id"))
            row_count = int(entry.get("row_count", 0))
            height = int(entry.get("height", 0))
            max_tokens = int(entry.get("max_row_tokens", 0))
            width = int(entry.get("width", 0))
            rows_match_height = row_count == height
            rows_fit_width = max_tokens <= width if width > 0 else True
            if not rows_match_height:
                validation_warnings.append(
                    f"map {map_id}: row_count {row_count} differs from height {height}"
                )
            if not rows_fit_width:
                validation_warnings.append(
                    f"map {map_id}: max_row_tokens {max_tokens} exceeds width {width}"
                )
            checks.append(
                {
                    "map_id": map_id,
                    "rows_match_height": rows_match_height,
                    "rows_fit_width": rows_fit_width,
                    "row_count": row_count,
                    "height": height,
                    "max_row_tokens": max_tokens,
                    "width": width,
                }
            )
    return checks


if __name__ == "__main__":
    raise SystemExit(main())
