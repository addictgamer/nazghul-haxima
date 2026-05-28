from __future__ import annotations

import json
from pathlib import Path

from pygame_haxima.data.scm_converter import ScmConverter


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    world = root.parent / "worlds" / "haxima-1.002"
    output = root / "converted_data"
    converter = ScmConverter()

    targets = {
        "terrains.scm": ("terrains.runtime.json", converter.convert_terrains),
        "zones.scm": ("zones.defines.json", converter.convert_defines),
        "world-map.scm": ("world-map.defines.json", converter.convert_defines),
    }
    for rel, (output_name, convert_fn) in targets.items():
        src = world / rel
        if not src.exists():
            print(f"skip: {src}")
            continue
        dst = output / output_name
        count = convert_fn(src, dst)
        print(f"converted {src.name}: {count} entries -> {dst.name}")

    maps_dir = world / "maps"
    maps_out_dir = output / "maps"
    map_files = sorted(maps_dir.glob("*.scm"))
    map_index: list[dict[str, object]] = []
    for map_file in map_files:
        out_file = maps_out_dir / f"{map_file.stem}.map.json"
        count = converter.convert_map_file(map_file, out_file)
        map_index.append({"source": map_file.name, "output": out_file.name, "map_count": count})
        print(f"converted {map_file.name}: {count} map(s) -> maps/{out_file.name}")
    (maps_out_dir / "index.json").write_text(json.dumps(map_index, indent=2), encoding="utf-8")
    print(f"wrote maps index: maps/index.json ({len(map_index)} files)")

    places_dir = world / "places"
    places_out_dir = output / "places"
    place_files = sorted(places_dir.glob("*.scm"))
    place_index: list[dict[str, object]] = []
    for place_file in place_files:
        out_file = places_out_dir / f"{place_file.stem}.place.json"
        count = converter.convert_place_file(place_file, out_file)
        place_index.append({"source": place_file.name, "output": out_file.name, "place_count": count})
        print(f"converted {place_file.name}: {count} place(s) -> places/{out_file.name}")
    (places_out_dir / "index.json").write_text(json.dumps(place_index, indent=2), encoding="utf-8")
    print(f"wrote places index: places/index.json ({len(place_index)} files)")

    townsfolk_init = world / "townsfolk" / "init.scm"
    townsfolk_out = output / "townsfolk.runtime.json"
    if townsfolk_init.exists():
        count = converter.convert_townsfolk(world, townsfolk_init, townsfolk_out)
        print(f"converted townsfolk: {count} files -> {townsfolk_out.name}")
    else:
        print(f"skip: {townsfolk_init}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
