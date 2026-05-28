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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
