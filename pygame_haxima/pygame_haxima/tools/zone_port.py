from __future__ import annotations

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
